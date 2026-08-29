"""Static backend-hygiene gate — the Phase 3 lesson-set, machine-enforced.

Call check() at the top of a backend phase gate. Raises SystemExit(1) on the
first violation so the run halts and Claude fixes it before the 7B repeats it.
"""
import pathlib
import re
import sys

BACKEND = pathlib.Path("B:/inky_code/finance-os/backend")
ROUTERS = BACKEND / "routers"

# routes that legitimately have a trivial body
_OK_TRIVIAL = re.compile(r"return\b|raise\b|yield\b|=\s|await\b|\w+\(")


def _iter_py(root: pathlib.Path):
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


# heavy / uninstalled deps the 7B keeps reaching for (Phase 6 lesson) — this box
# has only fastapi + uvicorn + numpy; RAG/embeddings must stay dep-free
_BANNED_DEPS = re.compile(
    r"\b(import|from)\s+(faiss|torch|sentence_transformers|transformers|sklearn|"
    r"scipy|tensorflow|openai|langchain|chromadb)\b"
)


def check():
    violations: list[str] = []

    for p in _iter_py(BACKEND):
        src = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(BACKEND).as_posix()
        m = _BANNED_DEPS.search(src)
        if m:
            violations.append(f"{rel}: imports '{m.group(2)}' — not installed on this box; keep it stdlib+numpy")

    # calculations + agents modules must be framework-free (Phase 4/5 lesson)
    for sub in ("calculations", "agents"):
        d = BACKEND / "services" / sub
        if not d.is_dir():
            continue
        for p in _iter_py(d):
            src = p.read_text(encoding="utf-8", errors="replace")
            rel = p.relative_to(BACKEND).as_posix()
            if re.search(r"\bAPIRouter\b|from\s+fastapi\b|import\s+fastapi\b", src):
                violations.append(f"{rel}: a services/{sub} module imports FastAPI / defines a router — keep it framework-free")

    for p in _iter_py(ROUTERS):
        src = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(BACKEND).as_posix()

        if re.search(r"from\s+routers\s+import\s", src):
            violations.append(f"{rel}: a router imports another router — move shared logic to services/")

        if re.search(r"=\s*Depends\(\s*\)", src):
            violations.append(f"{rel}: `Depends()` with no argument (auth is global middleware; DB uses a _db generator)")

        m = re.search(r"APIRouter\([^)]*prefix\s*=\s*['\"]([^'\"]+)['\"]", src)
        if m and "/api/finance" in m.group(1):
            violations.append(f"{rel}: APIRouter(prefix='{m.group(1)}') double-prefixes — use just the tab segment; app_factory adds /api/finance")

        # decorated route handlers whose body is only pass / ... / TODO
        for m in re.finditer(r"@router\.(get|post|put|delete|patch)\([^)]*\)\s*\n"
                             r"\s*(?:async\s+)?def\s+\w+\([^)]*\):\n"
                             r"((?:\s+.*\n)+?)(?=\s*@router\.|\Z|\S)", src):
            body = m.group(2)
            stripped = [ln.strip() for ln in body.splitlines() if ln.strip()
                        and not ln.strip().startswith(("#", '"""', "'''"))]
            if stripped and all(
                ln in ("pass", "...") or ln.lower().startswith("todo")
                for ln in stripped
            ):
                violations.append(f"{rel}: route `{m.group(0).splitlines()[1].strip()}` has a stub body ({stripped})")

    if violations:
        print("BACKEND HYGIENE GATE — fix these (Phase 3 lesson-set):", file=sys.stderr)
        for v in violations:
            print("  x " + v, file=sys.stderr)
        raise SystemExit(1)
    print("  ok: backend hygiene (no cross-router import, no bare Depends(), no stub routes)")


if __name__ == "__main__":
    check()
