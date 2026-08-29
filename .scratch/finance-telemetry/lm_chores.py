#!/usr/bin/env python
"""lm_chores.py <chore> [args] — hand NON-CODING chores to the local model
(llama-server :8080) so they cost zero Claude usage. Never touches git.

Chores:
  commit-msg <label>          read `git diff --cached` (stat + head), print a
                              house-style commit message (concise, grammar
                              sacrificed). Also -> raw/<label>-commitmsg.txt.
                              Nothing is committed; caller runs `git commit`.
  phase-summary <progress.md> condense a timestamped phase log into 3 bullets;
                              print + append to <progress.md> under "## Summary".
  ledger-digest [ledger.md]   condense the scout ledger into: carry-forward
                              tally, recurring fail tags, task types that
                              truncated. Print only.

All calls: temperature 0, capped tokens, raw JSON kept in raw/.
"""
from __future__ import annotations
import json, subprocess, sys, time, urllib.request, pathlib

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path("B:/inky_code")


def call(prompt: str, max_tokens: int, tag: str) -> str:
    body = json.dumps({
        "model": "model-a", "temperature": 0, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read().decode("utf-8"))
            (HERE / "raw").mkdir(exist_ok=True)
            (HERE / "raw" / f"{tag}.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8")
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15 * (attempt + 1))
    raise SystemExit(f"local model call failed after 3 tries: {last}")


def _git(args: list[str]) -> str:
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return p.stdout


def commit_msg(label: str) -> None:
    stat = _git(["diff", "--cached", "--stat"])
    body = _git(["diff", "--cached"])[:6000]
    if not stat.strip():
        raise SystemExit("nothing staged")
    prompt = (
        "Write a git commit message for this staged change. Rules: first line "
        "<=65 chars, imperative, prefix it with '" + label + ": '. Be extremely "
        "concise, sacrifice grammar for concision. Optional 1-3 terse bullet "
        "lines after a blank line. Output ONLY the message, no fence, no prose.\n\n"
        "=== git diff --cached --stat ===\n" + stat +
        "\n=== git diff --cached (truncated) ===\n" + body
    )
    msg = call(prompt, 400, f"{label}-commitmsg")
    (HERE / "raw" / f"{label}-commitmsg.txt").write_text(msg + "\n", encoding="utf-8")
    print(msg)


def phase_summary(progress_md: str) -> None:
    path = pathlib.Path(progress_md)
    log = path.read_text(encoding="utf-8")
    prompt = (
        "Below is a timestamped build-phase log. Summarise the OUTCOME in exactly "
        "3 markdown bullets: (1) tasks done / blocked, (2) notable retries or "
        "gate failures, (3) anything a human must check. Terse, grammar "
        "sacrificed. Output only the 3 bullets.\n\n" + log[-6000:]
    )
    summary = call(prompt, 300, f"{path.stem}-summary")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n\n## Summary (local model)\n\n" + summary + "\n")
    print(summary)


def ledger_digest(ledger_md: str = "") -> None:
    path = pathlib.Path(ledger_md) if ledger_md else REPO / ".scratch/lm-ui-gaps/ledger.md"
    text = path.read_text(encoding="utf-8")
    prompt = (
        "This is the ui-gap-scout ledger. Produce: (A) an open carry-forward "
        "list (genuine drops + now-due deferred items), (B) fail tags that "
        "recurred >=2x with counts, (C) task ids/types where output truncated "
        "or degraded. Markdown, terse. Output only that.\n\n" + text[-12000:]
    )
    print(call(prompt, 600, "ledger-digest"))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    chore = sys.argv[1]
    if chore == "commit-msg":
        commit_msg(sys.argv[2])
    elif chore == "phase-summary":
        phase_summary(sys.argv[2])
    elif chore == "ledger-digest":
        ledger_digest(sys.argv[2] if len(sys.argv) > 2 else "")
    else:
        raise SystemExit(f"unknown chore: {chore}\n{__doc__}")


if __name__ == "__main__":
    main()
