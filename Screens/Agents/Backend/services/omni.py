"""OmniRoute client — the one LLM seam (K-08): schema, max_tokens, fallback
chain, one llm_call spine event per call, no silent model.

The gateway at 127.0.0.1:8010 owns models, keys and routing; this module
resolves the rung chain from _routing.json in the spine dir, walks it top
down (one attempt per rung, one schema repair per rung), and reports the
outcome as an llm_call event. Gateway-down is an honest error — never a
fabricated reply, never a cached one.
"""

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

import settings_for_agents as cfg

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from Shared_By_All_Screens import spine  # noqa: E402


class OmniError(RuntimeError): ...
class OmniSchemaError(OmniError): ...
class OmniBudgetError(OmniError): ...

MODELS_CACHE_SECONDS = 60.0
_models_list_cache: Optional[list] = None
_models_list_cache_at: float = 0.0


def _default_routing_path() -> Path:
    return spine.spine_dir() / "_routing.json"


ROUTING_PATH: Path = _default_routing_path()


def load_routing() -> dict:
    """Read _routing.json from the spine dir, copying the default there
    on first use. The path is resolved per call so KAGE_SPINE_DIR set
    after import still wins (tests, phone migration)."""
    path = _default_routing_path()
    if not path.is_file():
        default = Path(__file__).resolve().parents[1] / "routing_default.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(default, path)
    return json.loads(path.read_text(encoding="utf-8"))


def _headers():
    headers = {"Content-Type": "application/json"}
    if cfg.GATEWAY_API_KEY:
        headers["Authorization"] = f"Bearer {cfg.GATEWAY_API_KEY}"
    return headers


def _make_client() -> httpx.AsyncClient:
    """Test hook: the seam tests swap in an httpx.MockTransport client."""
    return httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=5.0))


def _is_type(value, expected) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate(obj, schema: dict) -> list[str]:
    """Minimal JSON-schema check: type (incl. lists of types), properties,
    required, enum, maxLength, maxItems, items. Unknown keywords ignored.
    [] when valid."""
    errors: list[str] = []

    def check(value, sch, path):
        label = path or "value"
        expected = sch.get("type")
        if expected is not None:
            allowed = expected if isinstance(expected, list) else [expected]
            if not any(_is_type(value, t) for t in allowed):
                errors.append(f"{label}: expected type {expected}")
                return
        if "enum" in sch and value not in sch["enum"]:
            errors.append(f"{label}: not one of {sch['enum']!r}")
        if isinstance(value, str) and "maxLength" in sch and len(value) > sch["maxLength"]:
            errors.append(f"{label}: longer than {sch['maxLength']}")
        if isinstance(value, list):
            if "maxItems" in sch and len(value) > sch["maxItems"]:
                errors.append(f"{label}: more than {sch['maxItems']} items")
            items = sch.get("items")
            if isinstance(items, dict):
                for index, entry in enumerate(value):
                    check(entry, items, f"{label}[{index}]")
        if isinstance(value, dict):
            for name in sch.get("required") or []:
                if name not in value:
                    errors.append(f"{label}: missing required {name!r}")
            for name, sub in (sch.get("properties") or {}).items():
                if name in value:
                    check(value[name], sub, f"{label}.{name}")

    check(obj, schema or {}, "")
    return errors


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        newline = stripped.find("\n")
        if newline != -1:
            stripped = stripped[newline + 1:]
    if stripped.rstrip().endswith("```"):
        stripped = stripped.rstrip()[: stripped.rstrip().rfind("```")]
    return stripped.strip()


def _chain(routing: dict, task_class: str, model: Optional[str]) -> list[str]:
    models = routing.get("models") or {}
    if model:
        entry = models.get(model) or {}
        if not entry.get("enabled"):
            raise OmniError(f"model {model} is not enabled")
        chain = [model]
    else:
        task = (routing.get("tasks") or {}).get(task_class)
        if not task:
            raise OmniError(f"no model resolvable for {task_class}")
        chain = [
            rung for rung in (task.get("chain") or [])
            if (models.get(rung) or {}).get("enabled")
        ]
    if cfg.OMNIROUTE_MODEL and cfg.OMNIROUTE_MODEL not in chain:
        chain = [cfg.OMNIROUTE_MODEL] + chain
    if not chain:
        raise OmniError(f"no model resolvable for {task_class}")
    return chain


def _budget_check(task_class: str, agent_id: str, model: str, est_tokens: int) -> None:
    """No-op in K-08; K-09 gives it the real gate (raises OmniBudgetError,
    which skips the rung without an attempt)."""
    return None


def _cost_usd(model: str, usage: dict | None) -> float | None:
    """Prices arrive with K-09; until then the honest number is None."""
    return None


async def _post_rung(rung: str, max_tokens: int, messages: list[dict]):
    body = {"model": rung, "messages": messages, "max_tokens": max_tokens}
    try:
        async with _make_client() as client:
            response = await client.post(
                cfg.OMNIROUTE_URL + "/v1/chat/completions",
                headers=_headers(),
                json=body,
            )
    except httpx.HTTPError as exc:
        raise OmniError(
            f"OmniRoute unreachable at {cfg.OMNIROUTE_URL} — start the gateway first"
        ) from exc
    if response.status_code >= 400:
        raise OmniError(f"gateway error HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError as exc:
        raise OmniError("gateway returned non-JSON") from exc
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OmniError("gateway reply had no content") from exc
    if not text or not text.strip():
        raise OmniError("gateway returned an empty reply")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    return text, usage


async def ask_omni_detailed(system: str, prompt: str, *, model: Optional[str] = None,
                            max_tokens: int = 600, response_schema: dict | None = None,
                            task_class: str = "narrate", agent_id: str = "adhoc",
                            correlation_id: str | None = None) -> dict:
    """-> {"text": str, "object": dict | None, "model": str, "usage": dict | None,
           "rung_used": str, "chain": list[str], "degraded": bool}
    One llm_call spine event per call, on success or immediately before raising."""
    routing = load_routing()
    started = time.monotonic()

    def fail_event(chain: list[str], schema_valid: bool = False) -> None:
        spine.emit(
            "agents", "llm_call", agent_id,
            {
                "task_class": task_class,
                "tier": "none",
                "rung_used": "none",
                "chain": chain,
                "schema_valid": schema_valid,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "degraded": True,
                "unresolved_tokens": [],
            },
            model=None, tokens_in=None, tokens_out=None,
            cost_usd=None, correlation_id=correlation_id,
        )

    try:
        chain = _chain(routing, task_class, model)
    except OmniError:
        fail_event([])  # no attempt was possible; the event is still honest
        raise

    models = routing.get("models") or {}
    est_tokens = (len(system) + len(prompt)) // 4 + max_tokens

    schema_text = None
    if response_schema is not None:
        schema_text = ("\n\nRespond with exactly one JSON object matching this schema:\n"
                       + json.dumps(response_schema, sort_keys=True,
                                    separators=(",", ":")))

    last_error: Exception | None = None
    last_schema_failure = False

    for rung in chain:
        tier = (models.get(rung) or {}).get("tier") or "none"
        try:
            _budget_check(task_class, agent_id, rung, est_tokens)
        except OmniBudgetError:
            continue  # gate skip: no attempt, no event, chain still lists it

        base_messages = [
            {"role": "system",
             "content": system + schema_text if schema_text else system},
            {"role": "user", "content": prompt},
        ]
        messages = base_messages
        outcome = None
        for _attempt in range(2):  # one attempt, one schema repair
            try:
                text, usage = await _post_rung(rung, max_tokens, messages)
            except OmniError as exc:
                last_error, last_schema_failure = exc, False
                break  # next rung, fresh
            if response_schema is None:
                outcome = (text, usage, None)
                break
            parsed = None
            try:
                parsed = json.loads(_strip_fence(text))
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                errors = validate(parsed, response_schema)
            else:
                errors = ["reply was not a JSON object"]
            if not errors:
                outcome = (text, usage, parsed)
                break
            if _attempt == 0:
                messages = base_messages + [{
                    "role": "user",
                    "content": f"Return only the JSON object; errors: {', '.join(errors)}",
                }]
            else:
                last_error = OmniSchemaError(f"schema failed on {rung}: {errors}")
                last_schema_failure = True

        if outcome is None:
            continue

        text, usage, obj = outcome
        event_payload = {
            "task_class": task_class,
            "tier": tier,
            "rung_used": rung,
            "chain": chain,
            "schema_valid": True if response_schema is None else obj is not None,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "degraded": rung != chain[0],
            "unresolved_tokens": [],
        }
        spine.emit(
            "agents", "llm_call", agent_id, event_payload,
            model=rung,
            tokens_in=(usage or {}).get("prompt_tokens") if usage else None,
            tokens_out=(usage or {}).get("completion_tokens") if usage else None,
            cost_usd=_cost_usd(rung, usage),
            correlation_id=correlation_id,
        )
        return {
            "text": text.strip(),
            "object": obj,
            "model": rung,
            "usage": usage,
            "rung_used": rung,
            "chain": chain,
            "degraded": rung != chain[0],
        }

    # Every rung failed: one failure event (rung_used "none"), then raise.
    fail_event(chain)
    if last_schema_failure and isinstance(last_error, OmniSchemaError):
        raise last_error
    raise OmniError(
        f"all rungs failed for {task_class}: {last_error or 'no attempt made'}"
    )


async def ask_omni(system: str, prompt: str) -> str:
    return (await ask_omni_detailed(system, prompt))["text"]


async def list_models() -> list:
    """GET /v1/models off the gateway, cached 60s on success. Never caches a failure."""
    global _models_list_cache, _models_list_cache_at

    if _models_list_cache is not None and (time.monotonic() - _models_list_cache_at) < MODELS_CACHE_SECONDS:
        return _models_list_cache

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        try:
            response = await client.get(cfg.OMNIROUTE_URL + "/v1/models", headers=_headers())
        except httpx.HTTPError as exc:
            raise OmniError(
                f"OmniRoute unreachable at {cfg.OMNIROUTE_URL} — start the gateway first"
            ) from exc

    if response.status_code == 401:
        raise OmniError("gateway rejected the API key (401)")
    if response.status_code >= 400:
        raise OmniError(f"gateway error HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise OmniError("gateway returned non-JSON") from exc

    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
    _models_list_cache = ids
    _models_list_cache_at = time.monotonic()
    return ids
