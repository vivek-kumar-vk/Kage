# Model gateway — OmniRoute config note

The Model screen reports on an **OmniRoute** gateway (npm package `omniroute`, an
OpenAI-compatible AI gateway). OmniRoute keeps all of its own state in `~/.omniroute/`
(`storage.sqlite` + `server/`, `supervisor/`, `logs/`) — **not in this repo**. This file
records the config so a fresh machine can be brought to the same state by hand through
the dashboard at <http://127.0.0.1:8010>. **No secrets here.**

## Process

| | |
|---|---|
| Launcher | `Start_Inky/run_omniroute.py` (chained from `Start_Everything.bat`) |
| Bind | `127.0.0.1:8010` (`PORT=8010`, `OMNIROUTE_SERVER_HOST`/`API_HOST=127.0.0.1`) |
| Auth | `REQUIRE_API_KEY=true`, dashboard `requireLogin=true` |
| Secrets | `OMNIROUTE_JWT_SECRET` / `OMNIROUTE_API_KEY_SECRET` / `OMNIROUTE_INITIAL_PASSWORD` generated into repo-root `.env` (gitignored) by `run_omniroute.py` on first run |
| Health path | `GET /api/monitoring/health` (used by `server_for_model.py`) |

## Provider connections

One connection, the free tier:

| Field | Value |
|---|---|
| provider | `opencode` (OpenCode Free) |
| auth | none ("noauth") |
| active | yes, priority 1 |
| proxy | enabled |

## Models exposed (via `opencode`, 63)

Claude: `claude-fable-5`, `claude-opus-5`, `claude-opus-4-8/-4-7/-4-6/-4-5`,
`claude-sonnet-5`, `claude-sonnet-4-6/-4-5/-4`, `claude-haiku-4-5`
· Gemini: `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro`, `gemini-3-flash`
· GPT: `gpt-5.6-{sol,terra,luna}`, `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4{,-pro,-mini,-nano}`, `gpt-5.3-codex{,-spark}`, `gpt-5.2{,-codex}`, `gpt-5.1{,-codex-max,-codex,-codex-mini}`, `gpt-5{,-codex,-nano}`
· Grok: `grok-4.6`, `grok-4.5`, `grok-build-0.1`
· **GLM: `glm-5.2`, `glm-5.1`, `glm-5`**
· DeepSeek: `deepseek-v4-pro`, `deepseek-v4-flash`
· Qwen: `qwen3.6-plus`, `qwen3.5-plus`
· Kimi: `kimi-k3`, `kimi-k2.7-code`, `kimi-k2.6`, `kimi-k2.5`
· MiniMax: `minimax-m3`, `minimax-m2.7`, `minimax-m2.5`
· Free: `deepseek-v4-flash-free`, `mimo-v2.5-free`, `ling-3.0-flash-fin-free`,
`nemotron-3-ultra-free`, `nemotron-3.5-lightning-free`, `laguna-s-2.1-free`,
`muse-spark-1.2{,-contributor-free}`, `big-pickle`, `grok-build-0.1`

> **CONFIRM:** the persisted config has no model literally named "GLM Flash 5.3" —
> the GLM family present is `glm-5 / 5.1 / 5.2`. Update this line once the intended
> default model is pinned.

## Model aliases (dashboard → `modelAliases`)

```
claude-sonnet-4-6            -> agy/claude-sonnet-4-6
claude-opus-4-6-thinking     -> agy/claude-opus-4-6-thinking
gemini-3.1-pro               -> agy/gemini-pro-agent
gemini-3.6-flash-low         -> agy/gemini-3.6-flash-low
gemini-3.1-flash-lite-preview-> gemini/gemini-3.1-flash-lite
```

## API key for this screen

| | |
|---|---|
| name | `kage-model-screen` |
| prefix | `sk-4dea…` (full value in repo-root `.env` as `GATEWAY_API_KEY`) |
| model access | all |
| created | 2026-08-30 |

## Features enabled

Semantic cache (TTL 30 min, max 100) · prompt cache (`auto`) · request compression
(`cavemanConfig`, compresses `user` role, min 50 chars) · weekly auto-vacuum · call-log
pipeline · detailed logs.

## Rebuild on a fresh machine

1. `npm i -g omniroute`
2. `python Start_Inky/run_omniroute.py` — generates the `OMNIROUTE_*` secrets into `.env`, starts the gateway on 8010.
3. Dashboard → add provider connection `opencode` (no auth).
4. Dashboard → API keys → create `kage-model-screen`, copy value into `.env` as `GATEWAY_API_KEY=`.
5. Re-add the model aliases above if you want the short names.
6. Model screen (`:8001`) → `GET /api/model/overview` should return `state: ok` with the model list.
