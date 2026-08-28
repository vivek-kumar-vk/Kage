"""The one on/off switch for every local-model call in this project.

WHY THIS EXISTS
    Asked for directly: "a toggle switch somewhere to turn it on/off."
    call_the_local_model.py's ask(), embed() and describe_an_image()
    all check this before doing anything. Off means off completely -
    no call is attempted, not even a quick "is it worth it" check that
    would itself spend GPU time.

WHERE IT LIVES
    Shared_By_All_Agents/local_model_toggle.json - a single {"enabled":
    true/false}. Flipped from the Agents tab, or by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOGGLE_FILE = HERE / "local_model_toggle.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_enabled() -> bool:
    if not TOGGLE_FILE.exists():
        return True   # default on - the whole pipeline is opt-out, not opt-in
    try:
        return bool(json.loads(TOGGLE_FILE.read_text(encoding="utf-8")).get("enabled", True))
    except ValueError:
        return True


def set_enabled(enabled: bool) -> None:
    TOGGLE_FILE.write_text(json.dumps({"enabled": bool(enabled)}, indent=2), encoding="utf-8")


def main() -> None:
    print(f"local model calls are currently: {'ON' if is_enabled() else 'OFF'}")


if __name__ == "__main__":
    main()
