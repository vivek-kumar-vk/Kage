"""Static frontend-hygiene gate — the Phase 2 lesson-set, machine-enforced.

Call check() at the top of every frontend phase gate. Raises SystemExit(1) with a
concrete message on the first violation so the run halts and Claude fixes it
before the 7B repeats it in a later phase.
"""
import pathlib
import re
import sys

FRONTEND = pathlib.Path("B:/inky_code/finance-os/frontend")

BANNED_IMPORTS = (
    "framer-motion",
    "shadcn-ui",
    "@radix-ui",
    "use-sync-external-store",
    "react-markdown",
    "remark",
    "marked",
    "markdown-it",
)

# hooks that force a "use client"; directive
CLIENT_HOOKS = re.compile(
    r"\b(useState|useEffect|useLayoutEffect|useReducer|useContext|useRef|"
    r"useSyncExternalStore|usePathname|useRouter|useSearchParams|"
    r"useFinanceData|useSubmit)\b"
)
IMPORT_RE = re.compile(r"""^\s*import\s.*?from\s+['"]([^'"]+)['"]""", re.M)


def _iter_tsx():
    for p in FRONTEND.rglob("*.tsx"):
        if "node_modules" in p.parts or ".next" in p.parts:
            continue
        yield p
    for p in FRONTEND.rglob("*.ts"):
        if "node_modules" in p.parts or ".next" in p.parts:
            continue
        yield p


def check():
    violations: list[str] = []
    for p in _iter_tsx():
        src = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(FRONTEND).as_posix()
        imports = IMPORT_RE.findall(src)

        for imp in imports:
            for bad in BANNED_IMPORTS:
                if imp == bad or imp.startswith(bad + "/"):
                    violations.append(f"{rel}: bans-list import '{imp}'")
            if imp.startswith("../") and ("/components/" in imp or imp.endswith("/api") or "/lib/" in imp or "services/db" in imp):
                violations.append(f"{rel}: relative import '{imp}' — use the '@/' alias")

        # useFinanceData / useSubmit must come from @/lib/api (Phase 3 lesson)
        for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", src):
            names, srcmod = m.group(1), m.group(2)
            if ("useFinanceData" in names or "useSubmit" in names) and srcmod != "@/lib/api":
                violations.append(
                    f"{rel}: useFinanceData/useSubmit imported from '{srcmod}' — must be '@/lib/api'"
                )

        # barrel import of a non-existent index, or invented shared components
        # (Phase 6/7 lesson) — the only shared FE modules are the exact paths
        # @/components/finance/{Card,Skeleton,FormModal} + charts/InvestmentCharts
        for imp in imports:
            if imp == "@/components/finance":
                violations.append(f"{rel}: barrel import '@/components/finance' — no index file; import the exact path")
            if re.match(r"@/components/finance/(Button|Input|Select|Slider|Empty|Textarea|Modal|Table|constants|types)$", imp):
                violations.append(f"{rel}: import '{imp}' — that shared component/module does not exist; build it inline")

        # a client hook called inside a useEffect / async body (Phase 3 lesson)
        if re.search(r"useEffect\s*\(\s*(async\b|\(\s*\)\s*=>\s*\{)[^}]*\buseFinanceData\s*\(", src, re.S):
            violations.append(f"{rel}: useFinanceData() called inside useEffect — it is a top-level hook")

        # client hook without the directive on line 1
        if CLIENT_HOOKS.search(src):
            first = (src.lstrip().splitlines()[0] if src.strip() else "").strip()
            if first not in ('"use client";', "'use client';"):
                violations.append(f"{rel}: uses a client hook but line 1 is not a use-client directive")

    # root layout must stay a server component
    root_layout = FRONTEND / "app" / "layout.tsx"
    if root_layout.exists():
        s = root_layout.read_text(encoding="utf-8", errors="replace")
        if '"use client"' in s or CLIENT_HOOKS.search(s):
            violations.append("app/layout.tsx: root layout must be a server component (no 'use client', no client hooks)")

    if violations:
        print("FRONTEND HYGIENE GATE — fix these (Phase 2 lesson-set):", file=sys.stderr)
        for v in violations:
            print("  x " + v, file=sys.stderr)
        raise SystemExit(1)
    print("  ok: frontend hygiene (deps allow-list, @/ alias, use-client, server root layout)")


if __name__ == "__main__":
    check()
