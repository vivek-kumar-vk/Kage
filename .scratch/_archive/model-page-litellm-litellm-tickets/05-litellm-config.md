# T5 — config.yaml: providers, models, routing, fallback

Type: grilling
Status: open
Blocked by: (none)
Blocks: 06

## Question

Which providers to front (Anthropic API / OpenAI / local llama.cpp 8080-8081 /
Ollama at 11434 — `Main_Menu` already reads Ollama `/api/tags` live). Fallback
chains, routing strategy (`simple-shuffle` / `latency-based` / `usage-based`),
retries, `LITELLM_MASTER_KEY`. Commit a generic `config.yaml`; real values in
`.env`. Needs the user's actual providers/keys.

## Answer (partial — keys deferred)

**Keys come later.** User has accounts with several providers but has **not
created API keys yet**; will do so "once the LiteLLM UI is up and running". So:

- `config.yaml` ships with provider `model_list` entries whose `api_key` is
  `os.environ/<VAR>` placeholders; `.env.example` lists the VAR names; LiteLLM
  starts fine with them unset (those models just report unhealthy until the user
  fills `.env` or adds keys via the UI).
- This ticket **no longer blocks bringing LiteLLM up** — T4 can stand the
  gateway + its UI up with zero working models; the user then creates keys and
  the Model screen shows them going healthy.

**Still open:** the exact provider list to pre-wire (Anthropic? OpenAI? Groq?
OpenRouter? + local Ollama/llama.cpp), fallback chains, routing strategy,
`LITELLM_MASTER_KEY` generation. Revisit after T4 when the user is in the UI.
