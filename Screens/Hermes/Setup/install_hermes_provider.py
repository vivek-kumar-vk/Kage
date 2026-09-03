"""Give every Hermes profile access to the OmniRoute gateway (D25.1).

WHAT THIS DOES
    Appends one entry to custom_providers in the Hermes install-wide
    config, so any profile can name `omniroute` as its provider and
    reach the gateway's model list - DeepSeek included - instead of
    each profile carrying its own endpoint.

WHAT IT DELIBERATELY DOES NOT DO
    Change the default model. Declaring a provider is additive and
    reversible; repointing the whole fleet is a different decision, and
    not one to make as a side effect of wiring. Opt a profile in by
    hand:

        model:
          default: deepseek-v4-flash-free
          provider: omniroute

    Rewrite the file through a YAML dumper. Hermes' config.yaml carries
    a long comment block documenting fallback providers, and safe_dump
    would silently delete all of it. This appends text and leaves every
    existing byte alone. If custom_providers already exists it stops and
    says so rather than guessing how to merge.

ABOUT THE KEY
    Hermes' custom_providers takes a literal api_key, not an env name,
    so this copies GATEWAY_API_KEY out of the repo's .env into the
    Hermes config. That file lives in %LOCALAPPDATA%\hermes, outside
    this repo and outside git (CLAUDE.md Rule 7) - but it is a real key
    on disk, which is worth knowing.

RUN IT
    cd <repo root>
    .venv\Scripts\python Screens\Hermes\Setup\install_hermes_provider.py
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

# This file sits at  Screens/Hermes/Setup/install_hermes_provider.py
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Backend"))

import settings_for_hermes as cfg  # noqa: E402

# Confirmed with a real completion call through the gateway, not read off
# its /v1/models list - that list advertises routes which answer 402 or
# "Model is unavailable". Flash is the cheapest of the working three.
DEFAULT_MODEL = "cfp/deepseek-ai/deepseek-v4-flash-0731"


def gateway_key() -> str:
    """GATEWAY_API_KEY, from the environment or the repo's .env.

    One small reader, not a shared loader - this screen stays a complete
    independent component (Rule 5).
    """
    import os

    if os.environ.get("GATEWAY_API_KEY"):
        return os.environ["GATEWAY_API_KEY"]
    env_file = cfg.PROJECT_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GATEWAY_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def main() -> int:
    config_path = cfg.HERMES_CONFIG
    if not config_path.is_file():
        print(f"  no Hermes config at {config_path}")
        print("  install Hermes Agent first, or set HERMES_HOME")
        return 1

    text = config_path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(text) or {}

    existing = loaded.get("custom_providers")
    if existing is not None:
        names = [p.get("name") for p in existing if isinstance(p, dict)]
        if cfg.GATEWAY_PROVIDER_NAME in names:
            print(f"  provider '{cfg.GATEWAY_PROVIDER_NAME}' already declared"
                  " - nothing to do")
            return 0
        print(f"  custom_providers already exists with: {', '.join(map(str, names))}")
        print("  not merging automatically. Add this entry by hand:")
        print(f"""
  - name: {cfg.GATEWAY_PROVIDER_NAME}
    base_url: {cfg.GATEWAY_BASE_URL.rstrip('/')}/v1
    api_key: <GATEWAY_API_KEY from .env>
    default_model: {DEFAULT_MODEL}
""")
        return 2

    key = gateway_key()
    if not key:
        print("  GATEWAY_API_KEY is not in the environment or .env.")
        print("  Create it in the OmniRoute dashboard (Endpoints -> new key),")
        print("  put it in .env as GATEWAY_API_KEY=, then run this again.")
        return 1

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_suffix(f".yaml.backup-{stamp}")
    shutil.copy2(config_path, backup)
    print(f"  backed up  {backup.name}")

    block = f"""
# ── Kage gateway ──────────────────────────────────────────────────────
# Added by Screens/Hermes/Setup/install_hermes_provider.py (D25.1).
# One endpoint every profile can name, so model access is configured in
# one place. Point a profile at it with:
#   model:
#     default: {DEFAULT_MODEL}
#     provider: {cfg.GATEWAY_PROVIDER_NAME}
custom_providers:
  - name: {cfg.GATEWAY_PROVIDER_NAME}
    base_url: {cfg.GATEWAY_BASE_URL.rstrip('/')}/v1
    api_key: {key}
    default_model: {DEFAULT_MODEL}
"""
    config_path.write_text(
        text.rstrip("\n") + "\n" + block, encoding="utf-8"
    )
    print(f"  declared provider '{cfg.GATEWAY_PROVIDER_NAME}'"
          f" -> {cfg.GATEWAY_BASE_URL.rstrip('/')}/v1")
    print(f"  {len(text.splitlines())} existing lines left untouched")
    print()
    print("  next: opt a profile in, e.g.")
    print(f"    %LOCALAPPDATA%\hermes\profiles\<name>\config.yaml")
    print(f"      model: {{ default: {DEFAULT_MODEL},"
          f" provider: {cfg.GATEWAY_PROVIDER_NAME} }}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
