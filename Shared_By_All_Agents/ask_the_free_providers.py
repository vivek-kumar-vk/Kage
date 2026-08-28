"""Ask every free LLM provider INKY has a key for, one small question.

WHAT THIS IS
    An importable module for Shared_By_All_Agents (plus a runnable
    script). For each provider found in
    Secrets_Keys/my_api_keys_and_passwords.md it fires ONE real chat
    completion with the prompt below and reports latency, token counts
    and outcome.

        "Explain INKY's folder-is-a-screen invariant in 2 sentences"

WHY THE MODEL NAME IS NEVER HARDCODED
    Working rule: never hardcode a model name - read the provider's
    live list first. So each sweep is two requests per provider:
    GET the live model list, pick a chat model from it (excluding
    embed/whisper/tts/guard style models), then POST one completion.
    The only preference applied when picking is cheapness: shorter
    instruct-style ids win, because this probe wants a quick answer,
    not a clever one.

WHERE THE KEYS COME FROM AND WHERE THEY NEVER GO
    Keys are read straight from Secrets_Keys/my_api_keys_and_passwords.md
    at call time, using the same parse as the Models screen: find the
    `Provider id` row, take the `Key` row underneath it; last duplicate
    id wins; a blank key means "no key", which is a different answer
    from a wrong one. Key values are held only long enough to put them
    in an Authorization header. They are NEVER logged, printed,
    returned in results, or written to any ledger - result dicts are
    built field by field from a whitelist for exactly that reason.

THE LEDGERS
    Every attempt lands in the trace ledger
    (Shared_By_All_Screens/Trace_Ledger/traces_<date>.jsonl) as kind
    "model" with latency_ms / prompt_tokens / completion_tokens /
    outcome and one correlation_id shared by the whole sweep. A FAILED
    provider additionally gets a kind "error" row - those error rows
    are what this project uses as its errors record; there is no
    separate file. Ledger rows carry no key material by construction.

OFFLINE BEHAVIOUR
    No key for a provider -> outcome "skipped_no_key". No network ->
    every request fails softly into outcome "fail" with a reason;
    nothing raises. The pytest file skips its live test when there is
    no network so the suite stays green offline.
"""

from __future__ import annotations

import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent            # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                        # the inky folder

# The trace writer lives under Shared_By_All_Screens. Dual form because
# some callers run with the project root on sys.path and some with the
# Shared_By_All_Screens folder itself.
try:
    from Shared_By_All_Screens.trace_every_action import (
        new_correlation_id, trace,
    )
except ImportError:                               # pragma: no cover
    sys.path.insert(0, str(PROJECT_ROOT))
    from Shared_By_All_Screens.trace_every_action import (
        new_correlation_id, trace,
    )

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEYFILE = PROJECT_ROOT / "Secrets_Keys" / "my_api_keys_and_passwords.md"

PROMPT = "Explain INKY's folder-is-a-screen invariant in 2 sentences"

TIMEOUT_SECONDS = 30.0     # free tiers can be slow; 8s was too tight to answer in
USER_AGENT = "INKY/1.0 (personal dashboard; +local)"

# Same parse as Screens/Models/.../ask_each_provider.py - keep in step.
_PROVIDER_ROW = re.compile(r"^\|\s*Provider id\s*\|\s*(\S+)\s*\|")
_KEY_ROW = re.compile(r"^\|\s*Key\s*\|\s*(\S*)\s*\|")
_ACCOUNT_ROW = re.compile(r"^\|\s*Account id\s*\|\s*(\S+)\s*\|")

# Model ids that can answer a chat question vs ids that cannot.
_NOT_A_CHAT_MODEL = re.compile(
    r"(embed|whisper|tts|guard|moderation|rerank|clip|vision|image"
    r"|stable-?diffusion|speech|transcribe)", re.IGNORECASE)


# =====================================================================
# THE PROVIDERS
# =====================================================================
# kind      how to list models and how to chat
#   openai     OpenAI-compatible: GET {base}/models, POST {base}/chat/completions
#   cloudflare Workers AI: account-scoped model search, then the
#              OpenAI-compatible shim at /ai/v1
PROVIDERS = {
    "groq": {
        "label": "Groq",
        "kind": "openai",
        "base": "https://api.groq.com/openai/v1",
    },
    "openrouter": {
        "label": "OpenRouter",
        "kind": "openai",
        "base": "https://openrouter.ai/api/v1",
        "extra_headers": {"HTTP-Referer": "https://localhost/",
                          "X-Title": "INKY"},
    },
    "google_ai_studio": {
        "label": "Gemini (Google AI Studio)",
        "kind": "openai",           # Gemini's OpenAI-compatible endpoint
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "cerebras": {
        "label": "Cerebras",
        "kind": "openai",
        "base": "https://api.cerebras.ai/v1",
    },
    "mistral": {
        "label": "Mistral",
        "kind": "openai",
        "base": "https://api.mistral.ai/v1",
    },
    "github_models": {
        "label": "GitHub Models",
        "kind": "openai",
        "base": "https://models.github.ai/inference",
    },
    "cloudflare_workers_ai": {
        "label": "Cloudflare Workers AI",
        "kind": "cloudflare",
        "base": "https://api.cloudflare.com/client/v4",
        "needs_account_id": True,
    },
}


# =====================================================================
# READING THE KEYS (structure only - values never leave this module
# except inside an Authorization header)
# =====================================================================
def _read_secrets(path: Path | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """(keys, account_ids) keyed by Provider id. Last duplicate id wins."""
    keys: dict[str, str] = {}
    accounts: dict[str, str] = {}
    p = path or KEYFILE
    if not p.exists():
        return keys, accounts
    current = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        found = _PROVIDER_ROW.match(line)
        if found:
            current = found.group(1)
            continue
        if current is None:
            continue
        found = _KEY_ROW.match(line)
        if found:
            value = found.group(1)
            if value and value.lower() != "(not used)":
                keys[current] = value
            else:
                keys.pop(current, None)     # blank means no key
            continue
        found = _ACCOUNT_ROW.match(line)
        if found and found.group(1).lower() != "(not used)":
            accounts[current] = found.group(1)
    return keys, accounts


def read_account_id(provider: str) -> str | None:
    return _read_secrets()[1].get(provider)


def providers_with_keys() -> list[str]:
    """Which of OUR providers currently have a working-looking key."""
    keys = _read_secrets()[0]
    return [pid for pid in PROVIDERS if keys.get(pid)]


def has_network(host: str = "api.groq.com", port: int = 443,
                timeout: float = 3.0) -> bool:
    """Cheap reachability probe - used by tests to skip offline."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# =====================================================================
# HTTP - both helpers return (data, error). Neither ever raises, and
# neither puts the key anywhere but the request header.
# =====================================================================
def _headers(key: str, extra: dict | None = None) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json",
               "Content-Type": "application/json"}
    headers["Authorization"] = f"Bearer {key}"
    headers.update(extra or {})
    return headers


def _get_json(url: str, key: str, timeout: float = TIMEOUT_SECONDS,
              extra_headers: dict | None = None) -> tuple[object | None, str | None]:
    try:
        req = urllib.request.Request(url, headers=_headers(key, extra_headers))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None, f"HTTP {e.code} - key refused"
        if e.code == 429:
            return None, "HTTP 429 - free allowance spent for now"
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"could not connect ({e.reason})"
    except TimeoutError:
        return None, f"no answer within {timeout:g}s"
    except Exception as e:                        # noqa: BLE001
        return None, str(e)[:80]


def _post_json(url: str, key: str, payload: dict,
               timeout: float = TIMEOUT_SECONDS,
               extra_headers: dict | None = None) -> tuple[dict | None, str | None]:
    body = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers=_headers(key, extra_headers))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None, f"HTTP {e.code} - key refused"
        if e.code == 429:
            return None, "HTTP 429 - free allowance spent for now"
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"could not connect ({e.reason})"
    except TimeoutError:
        return None, f"no answer within {timeout:g}s"
    except Exception as e:                        # noqa: BLE001
        return None, str(e)[:80]



# =====================================================================
# PICKING A MODEL OFF THE LIVE LIST (never hardcoded)
# =====================================================================
def pick_chat_model(model_ids: list[str]) -> str | None:
    """A chat model from the LIVE list; cheap ones first. None if no fit.

    Preference order keeps the probe inexpensive: Cloudflare's own small
    @cf/meta instruct models win there, instruct-flavoured ids beat raw
    base models, un-versioned ids beat dated ones, shorter beats longer.
    """
    candidates = [m for m in model_ids if not _NOT_A_CHAT_MODEL.search(m)]
    if not candidates:
        return None

    def rank(mid: str) -> tuple:
        cloudflare_meta = 0 if "@cf/meta/" in mid else 1
        instructy = 0 if "instruct" in mid.lower() else 1
        versioned = 1 if re.search(r"\d{4}-\d{2}", mid) else 0
        return (cloudflare_meta, instructy, versioned, len(mid), mid)

    return sorted(candidates, key=rank)[0]


def _list_models(provider_id: str, cfg: dict, key: str,
                 account_id: str | None) -> tuple[list[str], str | None]:
    """The provider's live model ids. Never a hardcoded catalogue."""
    if cfg["kind"] == "cloudflare":
        if not account_id:
            return [], "no Account id in the secrets file"
        url = (f"{cfg['base']}/accounts/{account_id}/ai/models/search"
               "?per_page=100&task=text-generation")
        data, err = _get_json(url, key)
        if err:
            return [], err
        rows = (data or {}).get("result") or []
        return [r.get("name") for r in rows if r.get("name")], None
    data, err = _get_json(f"{cfg['base']}/models", key,
                          extra_headers=cfg.get("extra_headers"))
    if err:
        return [], err
    rows = (data or {}).get("data") or []
    return [r.get("id") for r in rows if r.get("id")], None



# =====================================================================
# THE ASK
# =====================================================================
def ask_one(provider_id: str, prompt: str = PROMPT,
            timeout: float = TIMEOUT_SECONDS,
            secrets_path: Path | None = None) -> dict:
    """One real completion on one provider. NEVER includes the key.

    Outcome is exactly one of:
        ok              answered; latency/tokens filled in
        fail            reached for it, did not get an answer (reason set)
        skipped_no_key  no usable key in the secrets file - nothing sent
    """
    cfg = PROVIDERS[provider_id]
    keys, accounts = _read_secrets(secrets_path)
    key = keys.get(provider_id)
    if not key:
        return {"provider": provider_id, "outcome": "skipped_no_key",
                "model": None, "latency_ms": None,
                "prompt_tokens": None, "completion_tokens": None,
                "answer_chars": None, "error": None}

    account_id = accounts.get(provider_id)
    model_ids, err = _list_models(provider_id, cfg, key, account_id)
    model = None
    if not err:
        model = pick_chat_model(model_ids)
        if not model:
            err = "live model list had no chat model"
    if err:
        return {"provider": provider_id, "outcome": "fail", "model": None,
                "latency_ms": None, "prompt_tokens": None,
                "completion_tokens": None, "answer_chars": None,
                "error": err}

    if cfg["kind"] == "cloudflare":
        url = f"{cfg['base']}/accounts/{account_id}/ai/v1/chat/completions"
    else:
        url = f"{cfg['base']}/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0,
    }
    started = time.perf_counter()
    data, err = _post_json(url, key, payload, timeout=timeout,
                           extra_headers=cfg.get("extra_headers"))
    latency_ms = int((time.perf_counter() - started) * 1000)
    if err:
        return {"provider": provider_id, "outcome": "fail", "model": model,
                "latency_ms": latency_ms, "prompt_tokens": None,
                "completion_tokens": None, "answer_chars": None,
                "error": err}

    usage = (data or {}).get("usage") or {}
    choices = (data or {}).get("choices") or []
    text = ((choices[0].get("message") or {}).get("content")) if choices else None
    return {
        "provider": provider_id,
        "outcome": "ok" if text else "fail",
        "model": model,
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "answer_chars": len(text) if text else 0,
        "error": None if text else "empty answer",
    }



def ask_all(providers: list[str] | None = None,
            prompt: str = PROMPT,
            log_to_ledger: bool = True,
            secrets_path: Path | None = None) -> list[dict]:
    """The full sweep. One correlation_id ties every row together.

    Trace-ledger writes: one kind="model" row per provider attempted;
    failures ALSO get a kind="error" row (the project's errors record -
    there is no separate errors file). Rows are built from explicit
    fields only, so a key value could only reach the ledger if somebody
    added it to that whitelist by hand.
    """
    wanted = list(providers) if providers else list(PROVIDERS)
    correlation_id = new_correlation_id()
    results = []
    for pid in wanted:
        if pid not in PROVIDERS:
            results.append({"provider": pid, "outcome": "fail", "model": None,
                            "latency_ms": None, "prompt_tokens": None,
                            "completion_tokens": None, "answer_chars": None,
                            "error": "unknown provider id"})
            continue
        result = ask_one(pid, prompt=prompt, secrets_path=secrets_path)
        results.append(result)

        if log_to_ledger:
            detail = {
                "model": result["model"],
                "latency_ms": result["latency_ms"],
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "outcome": result["outcome"],
                "correlation_id": correlation_id,
            }
            trace("track_m", "model", "free_provider_call", target=pid,
                  detail={k: v for k, v in detail.items() if v is not None},
                  outcome="ok" if result["outcome"] == "ok" else "fail",
                  duration_ms=result["latency_ms"],
                  correlation_id=correlation_id)
            if result["outcome"] == "fail":
                # the errors record: same ledger, kind "error".
                # A plain skip (no key) is honest absence, not a failure,
                # so it gets no error row.
                trace("track_m", "error", "free_provider_call_failed",
                      target=pid,
                      detail={"outcome": result["outcome"],
                              "reason": result["error"],
                              "correlation_id": correlation_id},
                      outcome="fail",
                      duration_ms=result["latency_ms"],
                      correlation_id=correlation_id)
    return results


# =====================================================================
# RUNNABLE
# =====================================================================
def main() -> int:
    print("Free-provider sweep - one real call per provider with a key.")
    print(f"Prompt: {PROMPT}")
    print(f"Network reachable: {has_network()}")
    print()
    results = ask_all()
    width = max(len(r["provider"]) for r in results) + 2
    for r in results:
        line = f"{r['provider']:<{width}} {r['outcome']}"
        if r["outcome"] == "ok":
            line += (f"  {r['latency_ms']} ms  "
                     f"tokens {r['prompt_tokens']}+{r['completion_tokens']}"
                     f"  ({r['model']})")
        elif r["error"]:
            line += f"  [{r['error']}]"
        print(line)
    print()
    print("Every row above is also in today's trace ledger;")
    print("failures additionally as kind=error (the errors record).")
    ok = sum(1 for r in results if r["outcome"] == "ok")
    skipped = sum(1 for r in results if r["outcome"] == "skipped_no_key")
    return 0 if (ok or skipped == len(results)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

