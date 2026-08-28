#!/usr/bin/env python
"""run_phase.py <manifest.json> [<manifest2.json> ...]

Autonomous build loop. NO GIT — files land in the working tree only; the user
commits after verifying. For each task in a manifest:
  snapshot target bytes -> resource-gate wait -> assemble prompt (contract +
  preamble + spec) -> POST llama-server -> strip fence -> write file
  -> machine gate (tsc for THIS file + eslint THIS file) -> fix-loop (<=max_retries)
  -> self-grill loop (<=grill_rounds: model reviews its file vs spec + the ask
     excerpt, outputs a corrected file or "PASS"; re-gate each revision)
  -> on unrecoverable failure: restore the snapshot, mark BLOCKED
  -> ledger + progress line -> cooldown.
After all tasks: `npx next build`, record status. Multiple manifests run in order.

Task shape:
  {"id": "...", "out": "app/.../X.tsx", "client": false, "spec": "...",
   "op": "write" | "rm"}   # op defaults to "write"; "rm" deletes `out`

Manifest adds (vs the earlier version): "ask_excerpt_file", "grill_rounds".
No "git" anywhere.
"""
from __future__ import annotations
import json, sys, time, subprocess, urllib.request, pathlib, re, os, shutil, datetime

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
HEALTH   = "http://127.0.0.1:8080/health"
HERE = pathlib.Path(__file__).resolve().parent

PREAMBLE = (
    "You are Model A. Output ONE complete file for the path below and nothing "
    "else: no prose, no explanation, no markdown fence. Next.js 16 App Router "
    "(output:export) + React 19 + Tailwind v4 + framer-motion ^13. This repo "
    "runs a PATCHED Next.js — follow THIS spec, not your training data.\n"
)


def log(progress: pathlib.Path, line: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    progress.parent.mkdir(parents=True, exist_ok=True)
    with progress.open("a", encoding="utf-8") as f:
        f.write(f"- {ts}  {line}\n")
    print(f"[{ts}] {line}", flush=True)


def strip_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```[a-zA-Z0-9_-]*\n(.*)\n```$", t, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"
    t = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", t)
    t = re.sub(r"\n```$", "", t)
    return t.strip() + "\n"


def free_ram_mb() -> int:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
            capture_output=True, text=True, timeout=30)
        return int(out.stdout.strip()) // 1024
    except Exception:
        return 99999


def free_vram_mb() -> int:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return 99999


def llama_up() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_llama(cmd: str, progress: pathlib.Path) -> None:
    if llama_up():
        return
    if not cmd:
        log(progress, "!! llama-server down and no llama_cmd given — waiting 5 min")
        for _ in range(10):
            time.sleep(30)
            if llama_up():
                return
        return
    log(progress, "restarting llama-server")
    subprocess.Popen(cmd, shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        time.sleep(5)
        if llama_up():
            log(progress, "llama-server back up")
            return
    log(progress, "!! llama-server did not come back")


def resource_gate(m: dict, progress: pathlib.Path) -> None:
    need_ram = m.get("min_free_ram_mb", 1800)
    need_vram = m.get("min_free_vram_mb", 700)
    waited = 0
    while True:
        ram, vram = free_ram_mb(), free_vram_mb()
        if ram >= need_ram and vram >= need_vram:
            return
        if waited % 300 == 0:
            log(progress, f"resource wait: free RAM {ram}MB (need {need_ram}), "
                          f"free VRAM {vram}MB (need {need_vram})")
        time.sleep(30)
        waited += 30
        if waited >= 3600:
            log(progress, "resource wait hit 1h ceiling — proceeding")
            return


def call_model(prompt: str, max_tokens: int, task_id: str, tag: str = "") -> str:
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
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read().decode("utf-8"))
            (HERE / "raw").mkdir(exist_ok=True)
            (HERE / "raw" / f"{task_id}{tag}.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8")
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"model call failed after 3 tries: {last}")


def run_cmd(args: list[str], cwd: str) -> tuple[int, str]:
    if os.name == "nt":
        cmd = subprocess.list2cmdline(args)
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           shell=True, timeout=900)
    else:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=900)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def gate(cwd: str, out_rel: str) -> tuple[bool, str]:
    """True + '' if this file passes; else False + errors. Only tsc errors whose
    path is this file block (siblings not built yet are tolerated); eslint on
    this file blocks."""
    norm = out_rel.replace("\\", "/")
    _, tsc_out = run_cmd(["npx", "tsc", "--noEmit"], cwd)
    mine = [ln for ln in tsc_out.splitlines()
            if norm in ln.replace("\\", "/") and "error TS" in ln]
    rc_l, lint_out = run_cmd(["npx", "eslint", out_rel], cwd)
    problems = []
    if mine:
        problems.append("TypeScript errors in this file:\n" + "\n".join(mine))
    if rc_l != 0:
        tail = "\n".join(lint_out.strip().splitlines()[-30:])
        problems.append("ESLint:\n" + tail)
    return (not problems), "\n\n".join(problems)


def self_grill(out_abs: pathlib.Path, cwd: str, out_rel: str, base: str,
               ask_excerpt: str, rounds: int, task_id: str,
               max_tokens: int, progress: pathlib.Path) -> tuple[int, str]:
    """Model reviews its own file against the spec + the ask, up to `rounds`.
    Keeps the last machine-gate-clean version. Returns (rounds_used, verdict)."""
    last_good = out_abs.read_text(encoding="utf-8")
    used = 0
    for rnd in range(1, rounds + 1):
        used = rnd
        resource_gate({"min_free_ram_mb": 1500, "min_free_vram_mb": 600}, progress)
        review = (
            base
            + "\n\n=== SELF-REVIEW ROUND " + str(rnd) + " ===\n"
            + "Here is the file you produced:\n\n" + last_good
            + "\n\n=== THE ASK (what the finished screen must feel like) ===\n"
            + ask_excerpt
            + "\n\n=== YOUR JOB NOW ===\n"
            "Go through the SPEC line by line and the ASK point by point. For "
            "each, decide MET or NOT-MET with one line of evidence from the "
            "file. If EVERYTHING is met, reply with exactly the single word "
            "PASS and nothing else. Otherwise reply with the COMPLETE corrected "
            "file (only the file, no prose, no fence)."
        )
        resp = strip_fence(call_model(review, max_tokens, task_id, tag=f"-grill{rnd}"))
        if resp.strip().upper().rstrip(".") == "PASS":
            log(progress, f"{task_id}: self-grill PASS at round {rnd}")
            out_abs.write_text(last_good, encoding="utf-8")
            return used, "self-grill PASS"
        out_abs.write_text(resp, encoding="utf-8")
        ok, errs = gate(cwd, out_rel)
        if ok:
            last_good = resp
            log(progress, f"{task_id}: self-grill round {rnd} revised + gate clean")
        else:
            log(progress, f"{task_id}: self-grill round {rnd} revision broke the "
                          f"gate — reverting to last clean, stopping grill")
            out_abs.write_text(last_good, encoding="utf-8")
            return used, "self-grill stopped (revision broke gate)"
    out_abs.write_text(last_good, encoding="utf-8")
    return used, f"self-grill ran {rounds} rounds, no PASS"


def ledger_entry(ledger: pathlib.Path, task_id: str, out_rel: str, verdict: str,
                 retries: int, grill_rounds: int, grill_verdict: str, tail: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = (f"\n### {ts} · {task_id} · {out_rel}\n"
             f"- verdict: {verdict}\n- retries: {retries}\n"
             f"- self-grill: {grill_rounds} round(s) — {grill_verdict}\n"
             f"- gate: {'clean' if verdict != 'BLOCKED' else tail[:400].replace(chr(10), ' / ')}\n")
    with ledger.open("a", encoding="utf-8") as f:
        f.write(block)


def do_task(m: dict, t: dict, contract: str, ask_excerpt: str) -> str:
    cwd, repo = m["cwd"], m["repo"]
    progress = pathlib.Path(m["progress_file"])
    ledger = pathlib.Path(m["ledger_file"])
    out_rel = t["out"]
    out_abs = pathlib.Path(cwd) / out_rel
    max_retries = m.get("max_retries", 2)
    grill_rounds = t.get("grill_rounds", m.get("grill_rounds", 3))

    if t.get("op") == "rm":
        if out_abs.is_dir():
            shutil.rmtree(out_abs)
            log(progress, f"{t['id']}: removed dir {out_rel}")
        elif out_abs.exists():
            out_abs.unlink()
            log(progress, f"{t['id']}: removed {out_rel}")
        else:
            log(progress, f"{t['id']}: nothing to remove at {out_rel}")
        return "ok"

    # snapshot for restore-on-failure (works whether or not the file is tracked)
    snap = out_abs.read_text(encoding="utf-8") if out_abs.exists() else None

    client_line = ('First line MUST be exactly: "use client";  (with the quotes).\n'
                   if t.get("client") else
                   'Do NOT add "use client" unless the spec uses hooks/handlers.\n')
    base = (contract + "\n\n" + PREAMBLE + client_line +
            f"\nFILE: {out_rel}\n\nSPEC:\n{t['spec']}\n")

    resource_gate(m, progress)
    ensure_llama(m.get("llama_cmd", ""), progress)
    log(progress, f"{t['id']}: generating")

    raw = call_model(base, m.get("max_tokens", 2600), t["id"])
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    out_abs.write_text(strip_fence(raw), encoding="utf-8")

    ok, errs = gate(cwd, out_rel)
    retries = 0
    while not ok and retries < max_retries:
        retries += 1
        log(progress, f"{t['id']}: gate failed, retry {retries}")
        resource_gate(m, progress)
        ensure_llama(m.get("llama_cmd", ""), progress)
        fix = (base + "\n\nThe file you produced has these problems:\n" + errs +
               "\n\nReturn the COMPLETE corrected file. Output only the file.")
        raw = call_model(fix, m.get("max_tokens", 2600), t["id"], tag=f"-fix{retries}")
        out_abs.write_text(strip_fence(raw), encoding="utf-8")
        ok, errs = gate(cwd, out_rel)

    if not ok:
        if snap is not None:
            out_abs.write_text(snap, encoding="utf-8")
        elif out_abs.exists():
            out_abs.unlink()
        ledger_entry(ledger, t["id"], out_rel, "BLOCKED", retries, 0, "n/a", errs)
        log(progress, f"{t['id']}: BLOCKED after {retries} retries — snapshot restored")
        return "blocked"

    g_rounds, g_verdict = self_grill(out_abs, cwd, out_rel, base, ask_excerpt,
                                     grill_rounds, t["id"], m.get("max_tokens", 2600),
                                     progress)
    verdict = "clean" if retries == 0 else f"fixed-by-model({retries})"
    ledger_entry(ledger, t["id"], out_rel, verdict, retries, g_rounds, g_verdict, "")
    log(progress, f"{t['id']}: DONE ({verdict}; {g_verdict}) — left in working tree, no commit")
    return "ok"


def run_manifest(path: str) -> None:
    m = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    progress = pathlib.Path(m["progress_file"])
    contract = ""
    cf = m.get("contract_file")
    if cf and pathlib.Path(cf).exists():
        contract = pathlib.Path(cf).read_text(encoding="utf-8")
    ask_excerpt = ""
    af = m.get("ask_excerpt_file")
    if af and pathlib.Path(af).exists():
        ask_excerpt = pathlib.Path(af).read_text(encoding="utf-8")

    log(progress, f"=== PHASE {m['phase']} START ({len(m['tasks'])} tasks) === (no git)")
    tally = {"ok": 0, "blocked": 0, "error": 0}
    for i, t in enumerate(m["tasks"], 1):
        log(progress, f"--- task {i}/{len(m['tasks'])}: {t['id']} ---")
        try:
            tally[do_task(m, t, contract, ask_excerpt)] += 1
        except Exception as e:  # noqa: BLE001
            tally["error"] += 1
            log(progress, f"{t['id']}: EXCEPTION {e!r}")
        time.sleep(m.get("cooldown_s", 90))

    if m.get("final_build"):
        log(progress, "running next build")
        rc, out = run_cmd(["npx", "next", "build"], m["cwd"])
        tail = "\n".join(out.strip().splitlines()[-12:])
        log(progress, f"next build rc={rc}\n{tail}")

    log(progress, f"=== PHASE {m['phase']} DONE  ok={tally['ok']} "
                  f"blocked={tally['blocked']} error={tally['error']} ===")


def main() -> None:
    for path in sys.argv[1:]:
        try:
            run_manifest(path)
        except Exception as e:  # noqa: BLE001
            print(f"manifest {path} crashed: {e!r}", flush=True)
    print("ALL MANIFESTS DONE", flush=True)


if __name__ == "__main__":
    main()
