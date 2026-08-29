#!/usr/bin/env python
"""run_build.py <manifest0.json> [<manifest1.json> ...]

Finance OS V1 autonomous build loop. Backend-aware fork of
../finance-telemetry/run_phase.py — reuses its helpers, adds:

  * per-task "lang": "py" | "tsx"  (default from manifest "lang", else "tsx")
      - "py":  preamble = FastAPI/Python; gate = ruff check <file> + py-compile
               + optional per-task "pytest": "<-k expr>" run from backend cwd
      - "tsx": preamble + gate = run_phase's tsc(this-file)+eslint
  * manifest "gate_cmd": shell string run once at phase end from repo root.
      exit 0 => phase PASS. non-zero => phase FAIL and the whole run HALTS
      (later phases depend on earlier ones).
  * ONE consolidated report at the end -> progress/RUN_REPORT.md
      (per-phase ok/blocked/error counts, every gate_cmd rc, halt phase if any,
       + tail of each gate). No per-phase, no per-task notification.

NO GIT. Files land in the working tree; the user commits after verifying.
Scout (ui_gap_scout) still fires per task when manifest "scout" != false.
"""
from __future__ import annotations
import json, sys, time, pathlib, datetime, subprocess, os, re
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "finance-telemetry"))
import run_phase as rp  # noqa: E402

REPORT = HERE / "progress" / "RUN_REPORT.md"


def call_model_resilient(m, prompt, max_tokens, task_id, tag=""):
    """rp.call_model, but if it throws (llama-server crashed mid-run) restart the
    server via llama_cmd and try once more. llama-server on this box exits
    unpredictably under long load; this keeps the run going."""
    progress = pathlib.Path(m["progress_file"])
    try:
        return rp.call_model(prompt, max_tokens, task_id, tag=tag)
    except Exception as e:  # noqa: BLE001
        rp.log(progress, f"{task_id}: model call failed ({e!r}) — restarting llama-server")
        rp.ensure_llama(m.get("llama_cmd", ""), progress)
        time.sleep(10)
        return rp.call_model(prompt, max_tokens, task_id, tag=tag + "-r")

PREAMBLE_PY = (
    "You are Model A. Output ONE complete Python file for the path below and "
    "nothing else: no prose, no explanation, no markdown fence. Target: FastAPI "
    "+ stdlib sqlite3 + Pydantic v2, Python 3.11. Every DB open goes through "
    "backend/services/db.py:connect(). Follow THIS spec exactly, not your "
    "training data. Deterministic code, no cleverness.\n"
    "IMPORT DISCIPLINE: never write the same import line twice. Import ONLY from "
    "these FastAPI paths: `fastapi`, `fastapi.responses`, `fastapi.staticfiles`, "
    "`fastapi.middleware.cors`, `starlette.middleware.base`. There is NO "
    "`fastapi.middleware.gzip/session/state/chunked/deflate/proxy_headers` — do "
    "not invent submodules. If you catch yourself repeating a line, STOP and "
    "finish the file.\n"
    "MODULE PATHS: the process runs with cwd = finance-os/backend/. Import "
    "sibling modules as TOP-LEVEL names: `from services.db import connect`, "
    "`from startup import PassthroughAuth`, `from routers import overview`. "
    "NEVER a leading dot (`from .startup import`) and NEVER a `backend.` prefix "
    "(`from backend.services...`). Order imports stdlib-first, third-party, then "
    "local — but a wrong order is not worth a second attempt.\n"
)


def _normalize_py(text: str) -> str:
    """Deterministic fixes for the 7B's recurring import mistakes: backend/ is
    run as cwd, not a package — a leading dot or a `backend.` prefix is always
    wrong here."""
    out = []
    for ln in text.splitlines():
        ln = re.sub(r'^(\s*from )\.(\w)', r'\1\2', ln)          # from .x  -> from x
        ln = re.sub(r'^(\s*from )backend\.', r'\1', ln)          # from backend.x -> from x
        ln = re.sub(r'^(\s*import )backend\.', r'\1', ln)
        out.append(ln)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _runaway(text: str, limit: int = 6) -> str | None:
    """Detect the degenerate repetition loop (same non-trivial line N+ times)."""
    c = Counter(ln.strip() for ln in text.splitlines() if len(ln.strip()) > 12)
    ln, n = (c.most_common(1) or [("", 0)])[0]
    return f"line repeated {n}x (generation loop): {ln[:80]}" if n > limit else None


def _py_gate(cwd: str, out_rel: str, pytest_k: str | None) -> tuple[bool, str]:
    probs = []
    abs_p = pathlib.Path(cwd) / out_rel
    rc, out = rp.run_cmd(["python", "-c",
                          f"import ast,sys; ast.parse(open(r'{abs_p}',encoding='utf-8').read())"], cwd)
    if rc != 0:
        probs.append("SyntaxError:\n" + out.strip()[-1500:])
    # only real breakage: E9 syntax, F63 bad-compare, F7 stmt errors, F82 undefined
    # name. NO import-sorting / formatting / unused-import noise (a 7B won't win
    # style fights and they don't break anything).
    rc, out = rp.run_cmd(["python", "-m", "ruff", "check", "--select", "E9,F63,F7,F82",
                          "--no-cache", out_rel], cwd)
    if rc != 0:
        probs.append("ruff (real errors only):\n" + "\n".join(out.strip().splitlines()[-25:]))
    if not probs and pytest_k:
        rc, out = rp.run_cmd(["python", "-m", "pytest", "-q", "-k", pytest_k], cwd, timeout=600)
        if rc != 0:
            probs.append(f"pytest -k {pytest_k}:\n" + "\n".join(out.strip().splitlines()[-40:]))
    return (not probs), "\n\n".join(probs)


def do_task_lite(m: dict, t: dict, contract: str, ask: str, progress: pathlib.Path) -> str:
    cwd = t.get("cwd", m["cwd"])
    lang = t.get("lang", m.get("lang", "tsx"))
    out_rel = t["out"]
    out_abs = pathlib.Path(cwd) / out_rel
    max_retries = m.get("max_retries", 2)
    grill_rounds = t.get("grill_rounds", m.get("grill_rounds", 3))
    mt = m.get("max_tokens", 2600)

    if t.get("op") == "rm":
        if out_abs.exists():
            out_abs.unlink()
        rp.log(progress, f"{t['id']}: removed {out_rel}")
        return "ok"

    snap = out_abs.read_text(encoding="utf-8") if out_abs.exists() else None

    if lang in ("raw", "json", "css", "md", "sql", "text"):
        preamble = ("You are Model A. Output ONE complete file for the path below "
                    "and nothing else: no prose, no markdown fence.\n")
        client_line = ""

        def _raw_gate():
            if lang == "json":
                try:
                    json.loads((pathlib.Path(cwd) / out_rel).read_text(encoding="utf-8"))
                except Exception as e:  # noqa: BLE001
                    return False, f"invalid JSON: {e}"
            return True, ""
        gate_fn = _raw_gate
    elif lang == "py":
        preamble = PREAMBLE_PY
        client_line = ""
        gate_fn = lambda: _py_gate(cwd, out_rel, t.get("pytest"))
    else:
        preamble = rp.PREAMBLE
        client_line = ('First line MUST be exactly: "use client";  (with the quotes).\n'
                       if t.get("client") else
                       'Do NOT add "use client" unless the spec uses hooks/handlers.\n')
        gate_fn = lambda: rp.gate(cwd, out_rel)

    phase_ctx = (f"\n=== PHASE BRIEF (shared context for every file this phase) ===\n{ask}\n"
                 if ask else "")
    base = (contract + "\n\n" + preamble + client_line + phase_ctx +
            f"\nFILE: {out_rel}\n\nSPEC (this file only):\n{t['spec']}\n")

    rp.resource_gate(m, progress)
    rp.ensure_llama(m.get("llama_cmd", ""), progress)
    rp.log(progress, f"{t['id']}: generating ({lang})")
    def _emit(raw: str) -> tuple[bool, str]:
        txt = rp.strip_fence(raw)
        if lang == "py":
            txt = _normalize_py(txt)
        out_abs.parent.mkdir(parents=True, exist_ok=True)
        out_abs.write_text(txt, encoding="utf-8")
        loop = _runaway(txt)
        return (loop is None), (loop or "")

    raw = call_model_resilient(m, base, mt, t["id"])
    clean, loop_err = _emit(raw)
    ok, errs = (False, loop_err) if not clean else gate_fn()
    retries = 0
    while not ok and retries < max_retries:
        retries += 1
        rp.log(progress, f"{t['id']}: gate failed, retry {retries}")
        rp.resource_gate(m, progress)
        rp.ensure_llama(m.get("llama_cmd", ""), progress)
        fix = base + "\n\nThe file you produced has these problems:\n" + errs + \
            "\n\nReturn the COMPLETE corrected file. Output only the file. Do NOT "\
            "repeat any line. Use top-level imports (from services.db import ...), "\
            "never a leading dot, never a backend. prefix."
        raw = call_model_resilient(m, fix, mt, t["id"], tag=f"-fix{retries}")
        clean, loop_err = _emit(raw)
        ok, errs = (False, loop_err) if not clean else gate_fn()

    ledger = pathlib.Path(m["ledger_file"])
    if not ok:
        if snap is not None:
            out_abs.write_text(snap, encoding="utf-8")
        elif out_abs.exists():
            out_abs.unlink()
        rp.ledger_entry(ledger, t["id"], out_rel, "BLOCKED", retries, 0, "n/a", errs)
        rp.log(progress, f"{t['id']}: BLOCKED after {retries} retries — snapshot restored")
        return "blocked"

    # self_grill uses the module-global rp.gate; point it at our gate for this task
    _orig = rp.gate
    rp.gate = lambda c, o: gate_fn()
    try:
        g_rounds, g_verdict = rp.self_grill(out_abs, cwd, out_rel, base, ask,
                                            grill_rounds, t["id"], mt, progress)
    finally:
        rp.gate = _orig

    verdict = "clean" if retries == 0 else f"fixed-by-model({retries})"
    rp.ledger_entry(ledger, t["id"], out_rel, verdict, retries, g_rounds, g_verdict, "")
    rp.log(progress, f"{t['id']}: DONE ({verdict}; {g_verdict})")

    if m.get("scout", True):
        try:
            rp.run_scout(m, t, base, verdict, retries, g_rounds, g_verdict, ask, progress)
        except Exception as e:  # noqa: BLE001
            rp.log(progress, f"{t['id']}: scout EXCEPTION {e!r} (non-fatal)")
        time.sleep(m.get("scout_cooldown_s", 30))
    return "ok"


def run_manifest(path: str) -> dict:
    m = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    progress = pathlib.Path(m["progress_file"])
    contract = ""
    if m.get("contract_file") and pathlib.Path(m["contract_file"]).exists():
        contract = pathlib.Path(m["contract_file"]).read_text(encoding="utf-8")
    ask = ""
    if m.get("ask_excerpt_file") and pathlib.Path(m["ask_excerpt_file"]).exists():
        ask = pathlib.Path(m["ask_excerpt_file"]).read_text(encoding="utf-8")

    rp.log(progress, f"=== PHASE {m['phase']} START ({len(m['tasks'])} tasks) === (no git)")
    for sc in m.get("setup_cmds", []):
        rp.log(progress, f"setup: {sc}")
        p = subprocess.run(sc, cwd=m["repo"], shell=True, capture_output=True,
                           text=True, timeout=1800)
        rp.log(progress, f"setup rc={p.returncode} "
                         + "\n".join(((p.stdout or '') + (p.stderr or '')).strip().splitlines()[-6:]))
    tally = {"ok": 0, "blocked": 0, "error": 0}
    for i, t in enumerate(m["tasks"], 1):
        rp.log(progress, f"--- task {i}/{len(m['tasks'])}: {t['id']} ---")
        try:
            tally[do_task_lite(m, t, contract, ask, progress)] += 1
        except Exception as e:  # noqa: BLE001
            tally["error"] += 1
            rp.log(progress, f"{t['id']}: EXCEPTION {e!r}")
        time.sleep(m.get("cooldown_s", 50))

    gate_rc, gate_tail = 0, "(no gate_cmd)"
    if m.get("gate_cmd"):
        rp.log(progress, f"running gate_cmd: {m['gate_cmd']}")
        p = subprocess.run(m["gate_cmd"], cwd=m["repo"], shell=True,
                           capture_output=True, text=True, timeout=1800)
        gate_rc = p.returncode
        gate_tail = "\n".join(((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-20:])
        rp.log(progress, f"gate_cmd rc={gate_rc}\n{gate_tail}")

    rp.log(progress, f"=== PHASE {m['phase']} DONE ok={tally['ok']} "
                     f"blocked={tally['blocked']} error={tally['error']} gate_rc={gate_rc} ===")
    return {"phase": m["phase"], "tally": tally, "gate_rc": gate_rc, "gate_tail": gate_tail}


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now()
    results, halted_at = [], None
    for path in sys.argv[1:]:
        try:
            r = run_manifest(path)
        except Exception as e:  # noqa: BLE001
            r = {"phase": path, "tally": {"ok": 0, "blocked": 0, "error": 1},
                 "gate_rc": 99, "gate_tail": f"manifest crashed: {e!r}"}
        results.append(r)
        if r["gate_rc"] != 0:
            halted_at = r["phase"]
            break

    lines = [f"# Finance OS V1 — build run report",
             f"", f"- started: {started:%Y-%m-%d %H:%M}",
             f"- finished: {datetime.datetime.now():%Y-%m-%d %H:%M}",
             f"- halted at phase: **{halted_at}**" if halted_at else "- completed: **all phases**",
             f"", f"| phase | ok | blocked | error | gate_rc |",
             f"|---|---|---|---|---|"]
    for r in results:
        tl = r["tally"]
        lines.append(f"| {r['phase']} | {tl['ok']} | {tl['blocked']} | {tl['error']} | {r['gate_rc']} |")
    lines.append("")
    for r in results:
        lines.append(f"## phase {r['phase']} gate tail\n```\n{r['gate_tail']}\n```")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRUN REPORT -> {REPORT}\n" + "\n".join(lines), flush=True)
    print("BUILD RUN COMPLETE" if not halted_at else f"BUILD RUN HALTED AT {halted_at}", flush=True)


if __name__ == "__main__":
    main()
