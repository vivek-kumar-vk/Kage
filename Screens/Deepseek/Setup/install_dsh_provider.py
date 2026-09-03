"""Point DeepSeek Harness at the OmniRoute gateway (D24.1).

WHAT THIS DOES
    Adds one provider block to dsh's own settings.yaml:

        llm-pi-ai.providers.omniroute -> http://127.0.0.1:8003/v1

    and writes a profile overlay (omniroute-deepseek.yml) that makes an
    agent boot on a DeepSeek model through that provider.

WHY THROUGH THE GATEWAY
    dsh ships only DeepSeek-cloud LLM adapters, which was recorded as a
    blocker. It is not one: @deepseek-ai/dsh-llm-pi-ai accepts
    hand-declared OpenAI-compatible providers (`api: openai-completions`),
    and OmniRoute is exactly that. So the harness reaches DeepSeek models
    with no custom adapter written and no second API key held - one place
    model access is configured, which is the whole point of the gateway.

    A hand-declared route REQUIRES all three of api, baseURL and a
    non-empty models list, or dsh rejects it on save.

WHAT IT WILL NOT DO
    Write your key into a config file. The provider references
    GATEWAY_API_KEY by name; dsh reads it from the environment at boot.

    Clobber your settings. It backs up settings.yaml first, then inserts
    its one provider as text inside the existing providers block - every
    other provider, and every comment in the file, is left byte for byte
    as it was. A YAML round-trip would silently delete the comments that
    document the other providers, so this never does one. Running it
    twice changes nothing the second time.

RUN IT
    cd <repo root>
    .venv\\Scripts\\python Screens\\Deepseek\\Setup\\install_dsh_provider.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

# This file sits at  Screens/Deepseek/Setup/install_dsh_provider.py
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Backend"))

import settings_for_deepseek as cfg  # noqa: E402

# The DeepSeek models this gateway actually serves, each confirmed with a
# real completion call rather than read off its /v1/models list. The list
# advertises far more than it can deliver: the `-free` route answers
# "Model is unavailable" upstream, and the `opencode/` routes return 402
# (no credit). These three return 200.
#
# Flash is the default - cheapest of the three that works (Rule 2).
DEFAULT_MODEL = "cfp/deepseek-ai/deepseek-v4-flash-0731"

# id, display name, context window. The windows are deliberate
# under-estimates: dsh wants a number, and guessing low truncates a long
# prompt early, where guessing high fails the call outright.
GATEWAY_MODELS = (
    ("cfp/deepseek-ai/deepseek-v4-flash-0731", "DeepSeek V4 Flash", 65536),
    ("cfp/deepseek-ai/deepseek-v4-pro-0813", "DeepSeek V4 Pro", 65536),
    ("cfp/deepseek-ai/deepseek-r1-distill-qwen-32b", "DeepSeek R1 Distill 32B", 32768),
)

OVERLAY_NAME = "omniroute-deepseek.yml"


def provider_text(indent: int) -> str:
    """The provider block, indented to sit under `providers:`.

    Written as text rather than dumped, so the surrounding file keeps its
    comments. `indent` is the column the sibling provider names sit at,
    so this lines up with whatever style the file already uses.
    """
    pad = " " * indent
    inner = " " * (indent + 2)
    item = " " * (indent + 2) + "- "
    detail = " " * (indent + 4)
    lines = [
        pad + "# Kage gateway - added by Screens/Deepseek/Setup/install_dsh_provider.py",
        pad + "# (D24.1). One endpoint for every model dsh can reach, so model",
        pad + "# access is configured in one place. GATEWAY_API_KEY must be in the",
        pad + "# environment before `dsh web` - the key is never written to a file.",
        pad + cfg.HARNESS_PROVIDER + ":",
        inner + "displayName: OmniRoute (Kage gateway)",
        inner + "api: openai-completions",
        inner + "baseURL: " + cfg.GATEWAY_BASE_URL.rstrip("/") + "/v1",
        inner + "apiKeyEnv: GATEWAY_API_KEY",
        inner + "models:",
    ]
    for model_id, name, window in GATEWAY_MODELS:
        lines += [
            item + "id: " + model_id,
            detail + "name: " + name,
            detail + "contextWindow: " + str(window),
            detail + "maxTokens: 8192",
        ]
    return "\n".join(lines) + "\n"


def find_providers_block(lines):
    """Where `llm-pi-ai: providers:` ends, and how far its entries indent.

    Returns (line index to insert at, indent of the provider names), or
    None when the file has no such block - in which case the caller
    appends the whole section instead of guessing at its shape.
    """
    top = next((i for i, ln in enumerate(lines) if ln.rstrip() == "llm-pi-ai:"), None)
    if top is None:
        return None
    providers = next(
        (i for i in range(top + 1, len(lines)) if lines[i].strip() == "providers:"),
        None,
    )
    if providers is None:
        return None
    base = len(lines[providers]) - len(lines[providers].lstrip())
    entry_indent = None
    end = len(lines)
    for i in range(providers + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        indent = len(lines[i]) - len(lines[i].lstrip())
        if indent <= base and not stripped.startswith("#"):
            end = i                     # the providers mapping ended here
            break
        if entry_indent is None and indent > base and not stripped.startswith("#"):
            entry_indent = indent
    # Trailing blank lines belong after the insert, not before it.
    while end > providers + 1 and not lines[end - 1].strip():
        end -= 1
    return end, (entry_indent if entry_indent is not None else base + 2)


def overlay_text() -> str:
    """The profile patch that boots an agent on the gateway's DeepSeek."""
    return (
        "# Overlay: boot an agent on a DeepSeek model served by the OmniRoute\n"
        "# gateway (declared as llm-pi-ai.providers." + cfg.HARNESS_PROVIDER + " in\n"
        "# settings.yaml). Written by Kage:\n"
        "#   Screens/Deepseek/Setup/install_dsh_provider.py\n"
        "#\n"
        "# Use with:\n"
        "#   dsh --profile headless --patch ~/.dsh/" + OVERLAY_NAME + " \"your task\"\n"
        "#   dsh --profile web      --patch ~/.dsh/" + OVERLAY_NAME + " --no-open\n"
        "#\n"
        "# --patch is a LAUNCHER flag and must come before the app's own\n"
        "# args: `dsh web --patch X` fails with \"unknown option '--patch'\".\n"
        "#\n"
        "# GATEWAY_API_KEY must be in the environment first - the provider\n"
        "# references it by name so the key is never written into a file.\n"
        "- id: agent-default-model\n"
        "  name: '@deepseek-ai/dsh-agent-default-model'\n"
        "  config:\n"
        "    provider: " + cfg.HARNESS_PROVIDER + "\n"
        "    model: " + DEFAULT_MODEL + "\n"
    )


def main() -> int:
    settings_path = cfg.DSH_SETTINGS
    if not settings_path.parent.is_dir():
        print("  no dsh home at " + str(settings_path.parent))
        print("  install it first:  npm install -g @deepseek-ai/dsh")
        return 1

    text = settings_path.read_text(encoding="utf-8") if settings_path.is_file() else ""
    loaded = (yaml.safe_load(text) or {}) if text else {}
    declared = (loaded.get("llm-pi-ai") or {}).get("providers") or {}

    if cfg.HARNESS_PROVIDER in declared:
        print("  provider '" + cfg.HARNESS_PROVIDER + "' already declared - nothing to do")
    else:
        if settings_path.is_file():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = settings_path.with_name("settings.yaml.backup-" + stamp)
            shutil.copy2(settings_path, backup)
            print("  backed up  " + backup.name)

        lines = text.splitlines(keepends=True)
        found = find_providers_block(lines)
        if found is None:
            block = "\nllm-pi-ai:\n  providers:\n" + provider_text(4)
            settings_path.write_text(text.rstrip("\n") + "\n" + block, encoding="utf-8")
            print("  created llm-pi-ai.providers and added '"
                  + cfg.HARNESS_PROVIDER + "'")
        else:
            at, indent = found
            if at > 0 and lines[at - 1].strip():
                lines.insert(at, "\n")
                at += 1
            lines.insert(at, provider_text(indent))
            settings_path.write_text("".join(lines), encoding="utf-8")
            print("  inserted provider '" + cfg.HARNESS_PROVIDER + "' -> "
                  + cfg.GATEWAY_BASE_URL.rstrip("/") + "/v1")
            print("  kept " + str(len(declared))
                  + " other provider(s) and every comment")

    overlay = cfg.DSH_HOME / OVERLAY_NAME
    wanted = overlay_text()
    if overlay.is_file() and overlay.read_text(encoding="utf-8") == wanted:
        print("  overlay " + OVERLAY_NAME + " already correct")
    else:
        overlay.write_text(wanted, encoding="utf-8")
        print("  wrote overlay " + str(overlay))

    print()
    print("  next:")
    print(r"    1. start the gateway:  .venv\Scripts\python Start_Inky\run_omniroute.py")
    print('    2. export the key:     $env:GATEWAY_API_KEY = "<from .env>"')
    # --patch is a LAUNCHER flag: it must come before the app's own args,
    # so `dsh --profile web --patch X` works where `dsh web --patch X`
    # fails with "unknown option '--patch'".
    print("    3. start the harness:  dsh --profile web --patch "
          + str(overlay) + " --no-open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
