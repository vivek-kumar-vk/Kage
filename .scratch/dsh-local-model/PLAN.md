# Plan (parked): run the local model inside DeepSeek Harness (`dsh`)

Status: **not started** — parked 2026-08-29 at user's request. Resume after the
finance redesign.

## Goal

Run the local coder model (Qwen2.5-Coder-7B, llama-server on `:8080`) inside
`dsh` so the **Web UI (`http://127.0.0.1:3080`) shows every prompt, tool call,
and file write step-by-step** — "see exactly what the local model is doing."

## What dsh is

- DeepSeek AI's open-source agent harness. Repo:
  https://github.com/deepseek-ai/deepseek-harness (MIT, default branch `master`).
- Node.js + pnpm, "everything is a plugin" on the Cordis framework.
- **Developer preview — breaking changes expected.** Review `SAFETY.md`.
- Run from npm: `npx @deepseek-ai/dsh web` (Web UI at `:3080`, `--no-open` to
  skip the browser).
- Run from source:
  ```
  git clone https://github.com/deepseek-ai/deepseek-harness.git
  cd deepseek-harness && pnpm install && pnpm run build && pnpm dsh web
  ```
- Config: a `cordis.yml` with per-plugin `config:` blocks. Catalog:
  `docs/config-catalog.md`. Default model selection plugin
  `@deepseek-ai/dsh-agent-default-model` takes `{ provider, model }`.

## The blocker

dsh ships **only two LLM adapters** and **both target the DeepSeek cloud API**:
- `packages/llm/llm-deepseek` — direct fetch + in-repo translate, DeepSeek SSE.
- `packages/llm/llm-pi-ai` — same endpoint via `@earendil-works/pi-ai`.

Both expose `apiKey`, `baseURL`, `models`. **No OpenAI-generic / Ollama /
llama.cpp adapter exists.**

## Two ways forward (pick when resuming)

### A. baseURL gamble (fast, may fail)
Install dsh, set `llm-deepseek`'s `baseURL` → `http://127.0.0.1:8080/v1`, dummy
`apiKey`. Try plain chat + tool calls. Risk: DeepSeek-specific request fields
(`thinking` / `reasoningEffort`, files API, prompt caching) make llama-server
400. No graceful fallback if the wire shape diverges.

### B. Custom `llm-openai` adapter plugin (proper, ~half a day)
Follow `docs/cookbook/adding-an-llm-adapter.md`:
- One class `extends LlmAdapter`, `async *stream(opts): AsyncIterable<StreamChunk>`.
- `export const name = 'llm-openai'`, `inject = ['llm']`,
  `Config = z.object({ apiKey, baseURL, models })`,
  `apply(ctx, cfg){ ctx.llm.registerAdapter(['openai'], new OpenAIAdapter(cfg)) }`.
- Protocol obligations (from the cookbook):
  - emit `usage` BEFORE `finish`; nothing after `finish`.
  - tool-call `arguments` are RAW JSON strings end-to-end; stream as
    `argumentsDelta`; re-stringify at `block-end` if provider hands objects.
  - allocate block `index`es in first-seen order, reuse per block.
  - errors: THROW `LlmError` from `stream()` (transport/protocol) OR end with
    `finish {kind:'error'|'aborted'}` (in-band). Pick per failure class.
  - honor `options.signal`; unsupported option → `LlmError(...,'UNSUPPORTED_OPTION')`.
  - implement `resolveModel()` for model metadata (context, reasoning).
- Reference layout: `packages/llm/llm-deepseek` (wire types / serialize /
  transport / translate / adapter as separate files). SSE via
  `eventsource-parser`. Read `packages/llm/llm/src/types.ts` `StreamChunk` doc
  first.
- Register the plugin in `cordis.yml`, set default model
  `{ provider: 'openai', model: 'qwen2.5-coder-7b-instruct-q5_k_m' }`.

## Environment notes (2026-08-29)

- Node `v24.19.0`, npm `11.17.0`, **no pnpm** — `corepack enable` or
  `npm i -g pnpm` first (or just use `npx @deepseek-ai/dsh`).
- llama-server: `C:\inky_models\bin\llama-server.exe` build 10621, model
  `C:\inky_models\Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf`, OpenAI-compatible
  endpoint at `http://127.0.0.1:8080/v1`.
- Hardware is tight (RTX 3050 6 GB / 16 GB RAM) — running dsh's TS build +
  llama-server + Chrome at once will thrash. Sequence them.

## Cheaper alternative if dsh proves too heavy

Route `run_phase.py` model calls through the already-installed **Hermes CLI**
profile and watch `hermes -p <profile> chat --tui` — every step visible, no new
install. (The `ui_gap_scout` scout already runs this way.)
