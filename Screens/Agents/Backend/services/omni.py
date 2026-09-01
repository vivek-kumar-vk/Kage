"""OmniRoute client — the one LLM seam for agent asks (D6 / D12).

The gateway at 127.0.0.1:8003 owns models, keys and routing; this module only
speaks /v1/chat/completions to it. Gateway-down is an honest error the caller
surfaces as an event — never a fabricated reply.
"""

from typing import Optional

import httpx

import settings_for_agents as cfg


class OmniError(RuntimeError):
    pass


_model_cache: Optional[str] = None


def _headers():
    headers = {"Content-Type": "application/json"}
    if cfg.GATEWAY_API_KEY:
        headers["Authorization"] = f"Bearer {cfg.GATEWAY_API_KEY}"
    return headers


async def _resolve_model(client: httpx.AsyncClient) -> str:
    global _model_cache

    if cfg.OMNIROUTE_MODEL:
        return cfg.OMNIROUTE_MODEL

    if _model_cache:
        return _model_cache

    try:
        response = await client.get(cfg.OMNIROUTE_URL + "/v1/models", headers=_headers())
        data = response.json()
        ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
        if ids:
            _model_cache = ids[0]
            return _model_cache
    except Exception:
        pass

    return "gpt-4o-mini"


async def ask_omni(system: str, prompt: str) -> str:
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=5.0)) as client:
        payload["model"] = await _resolve_model(client)

        try:
            response = await client.post(
                cfg.OMNIROUTE_URL + "/v1/chat/completions",
                headers=_headers(),
                json=payload,
            )
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

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OmniError("gateway reply had no content") from exc

    if not text or not text.strip():
        raise OmniError("gateway returned an empty reply")

    return text.strip()
