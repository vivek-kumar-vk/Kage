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
from datetime import datetime, timedelta
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


def _prices_path() -> Path:
    return spine.spine_dir() / "_model_prices.json"


PRICES_PATH: Path = _prices_path()


def load_prices() -> dict:
    """{model: {"provider", "usd_per_1k_in", "usd_per_1k_out"}} from the
    spine dir, copying model_prices_default.json there on first use. Paid
    models have no row until the owner supplies prices (D-05): they are
    refused, never guessed."""
    path = _prices_path()
    if not path.is_file():
        default = Path(__file__).resolve().parents[1] / "model_prices_default.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(default, path)
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["model"]: row for row in rows}


def spend_today() -> dict:
    """Spend computed by reading the spine events files directly (no
    Storage HTTP — the seam must work when Storage is down). A null
    cost_usd counts as the full per_call_usd: the conservative reading of
    an absent number (Rule 22), never a fabricated zero."""
    routing = load_routing()
    per_call = (routing.get("budget") or {}).get("per_call_usd", 0.05)
    today = datetime.now(spine.IST).date()
    days_7 = {(today - timedelta(days=offset)).isoformat() for offset in range(7)}
    months = {day.strftime("%Y-%m") for day in
              [today] + [today - timedelta(days=offset) for offset in range(7)]}
    cost_today = 0.0
    calls = calls_t2 = calls_7d = calls_t2_7d = 0
    by_agent: dict[str, float] = {}
    for month in sorted(months):
        path = spine.spine_dir() / f"events_{month}.jsonl"
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue  # torn last line: skipped, never guessed
                if event.get("type") != "llm_call":
                    continue
                day = (event.get("ts") or "")[:10]
                tier = (event.get("payload") or {}).get("tier")
                cost = event.get("cost_usd")
                if cost is None:
                    cost = per_call
                if day == today.isoformat():
                    calls += 1
                    cost_today += cost
                    if tier == "T2":
                        calls_t2 += 1
                    agent = event.get("subject") or "unknown"
                    by_agent[agent] = by_agent.get(agent, 0.0) + cost
                if day in days_7:
                    calls_7d += 1
                    if tier == "T2":
                        calls_t2_7d += 1
    return {
        "day": today.isoformat(),
        "cost_usd": round(cost_today, 6),
        "calls": calls,
        "calls_t2": calls_t2,
        "calls_7d": calls_7d,
        "calls_t2_7d": calls_t2_7d,
        "by_agent": by_agent,
    }


def budget_status() -> dict:
    routing = load_routing()
    budget = routing.get("budget") or {}
    cap = budget.get("per_day_usd", 0.30)
    spend = spend_today()
    degraded = spend["cost_usd"] >= cap
    reason = None
    if degraded:
        # The ts of the event that crossed the cap, walked in file order.
        running = 0.0
        crossed_at = None
        path = spine.spine_dir() / f"events_{spend['day'][:7]}.jsonl"
        if path.is_file():
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if (event.get("type") != "llm_call"
                            or (event.get("ts") or "")[:10] != spend["day"]):
                        continue
                    running += event.get("cost_usd") if event.get("cost_usd") is not None \
                        else per_call
                    if running >= cap and crossed_at is None:
                        crossed_at = event["ts"]
                        break
        if crossed_at:
            reason = f"day cap {cap} reached at {crossed_at[11:16]}"
    t2_share = (spend["calls_t2_7d"] / spend["calls_7d"]) if spend["calls_7d"] else 0.0
    return {
        "degraded": degraded,
        "reason": reason,
        "spend_usd": spend["cost_usd"],
        "cap_usd": cap,
        "t2_share": round(t2_share, 4),
    }


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
    """The budget gate (K-09). Raises OmniBudgetError, checked in this
    order: no price, day cap, agent cap, call cap, T2 share. T0 (free)
    rungs are never blocked."""
    routing = load_routing()
    budget = routing.get("budget") or {}
    models = routing.get("models") or {}
    tier = (models.get(model) or {}).get("tier") or "none"
    row = load_prices().get(model)
    if row is None and tier != "T0":
        raise OmniBudgetError(f"no price for {model}")

    if tier == "T0":
        estimate = 0.0
    else:
        estimate = est_tokens / 1000.0 * max(row["usd_per_1k_in"], row["usd_per_1k_out"])

    spend = spend_today()
    per_day = budget.get("per_day_usd", 0.30)
    per_agent = budget.get("per_agent_day_usd", 0.10)
    per_call = budget.get("per_call_usd", 0.05)

    if tier != "T0" and spend["cost_usd"] + estimate > per_day:
        raise OmniBudgetError(
            f"day cap {per_day} reached at {datetime.now(spine.IST).strftime('%H:%M')}"
        )
    if tier != "T0" and spend["by_agent"].get(agent_id, 0.0) + estimate > per_agent:
        raise OmniBudgetError(f"agent cap {per_agent} reached for {agent_id}")
    if estimate > per_call:
        raise OmniBudgetError(f"call cap {per_call}")
    if tier == "T2":
        share = (spend["calls_t2_7d"] + 1) / (spend["calls_7d"] + 1)
        if share > budget.get("t2_share_max", 0.05):
            raise OmniBudgetError(
                f"t2 share {round(share, 4)} over {budget.get('t2_share_max', 0.05)}"
            )


def _cost_usd(model: str, usage: dict | None) -> float | None:
    """Real cost from real usage; None when the gateway sent no usage or
    the model has no price row. Never an estimate, never a zero (Rule 22)."""
    if not usage:
        return None
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")
    if tokens_in is None or tokens_out is None:
        return None
    row = load_prices().get(model)
    if row is None:
        return None
    return round(tokens_in / 1000.0 * row["usd_per_1k_in"]
                 + tokens_out / 1000.0 * row["usd_per_1k_out"], 6)


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
