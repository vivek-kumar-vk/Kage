"""Aggregator script that runs all Kage automated checks and reports a single pass/fail."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def get_repo_root() -> Path:
    """Resolve the repo root as two levels up from this script's location."""
    return Path(__file__).resolve().parent.parent


def run_screen_pytest(backend_dir: Path, name: str) -> Tuple[str, str, int]:
    """Run one screen's pytest suite (tests/ under the given Backend directory)."""
    tests_dir = backend_dir / "tests"

    if not tests_dir.is_dir():
        msg = f"SKIP: no tests dir at {tests_dir}"
        print(msg)
        return (name, "SKIP", 0)

    cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
        )
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        status = "PASS" if result.returncode == 0 else "FAIL"
        return (name, status, result.returncode)
    except Exception as e:
        print(f"ERROR running {name}: {e}", file=sys.stderr)
        return (name, "FAIL", 1)


def run_hygiene_gate(gate_path: Path, label: str) -> Tuple[str, str, int]:
    """Import a hygiene gate module by file path and run its check() function."""
    if not gate_path.is_file():
        print(f"ERROR: gate script not found at {gate_path}", file=sys.stderr)
        return (label, "FAIL", 1)

    module_name = gate_path.stem
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(gate_path))
        if spec is None or spec.loader is None:
            print(f"ERROR: could not create import spec for {gate_path}", file=sys.stderr)
            return (label, "FAIL", 1)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        print(f"ERROR loading gate module {label}: SystemExit({code})", file=sys.stderr)
        return (label, "FAIL", code)
    except Exception as e:
        print(f"ERROR loading gate module {label}: {e}", file=sys.stderr)
        return (label, "FAIL", 1)

    try:
        module.check()
        return (label, "PASS", 0)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        return (label, "FAIL", code)
    except Exception as e:
        print(f"UNEXPECTED ERROR in gate {label}: {e}", file=sys.stderr)
        return (label, "FAIL", 1)


def run_generator_gate(script_path: Path, label: str) -> Tuple[str, str, int]:
    """Run the structure-docs generator and assert it exits 0 (STORAGE_TAB_SPEC section 1)."""
    if not script_path.is_file():
        print(f"ERROR: generator not found at {script_path}", file=sys.stderr)
        return (label, "FAIL", 1)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.stderr:
            sys.stderr.write(result.stderr)
        status = "PASS" if result.returncode == 0 else "FAIL"
        return (label, status, result.returncode)
    except Exception as e:
        print(f"ERROR running {label}: {e}", file=sys.stderr)
        return (label, "FAIL", 1)


def print_summary(results: List[Tuple[str, str, int]]) -> None:
    """Print a formatted summary block of all check results."""
    print("\n==== run_checks summary ====")
    for name, status, _code in results:
        print(f"[{status}] {name}")
    print("=============================")


def main() -> int:
    """Run all automated checks and return 0 if all passed, 1 otherwise."""
    repo_root = get_repo_root()
    results: List[Tuple[str, str, int]] = []

    # 1. Per-screen pytest suites (a screen with no tests dir reports SKIP)
    results.append(run_screen_pytest(repo_root / "Screens" / "Learning" / "Backend", "learning pytest"))
    results.append(run_screen_pytest(repo_root / "Screens" / "Office" / "Backend", "office pytest"))
    results.append(run_screen_pytest(repo_root / "Screens" / "Agents" / "Backend", "agents pytest"))
    results.append(run_screen_pytest(repo_root / "Screens" / "Model" / "Backend", "model pytest"))
    results.append(run_screen_pytest(repo_root / "Screens" / "Storage" / "Backend", "storage pytest"))
    results.append(run_screen_pytest(repo_root / "Screens" / "Finance" / "Backend", "finance pytest"))
    results.append(run_screen_pytest(repo_root / "Main_Menu" / "Backend", "main_menu pytest"))

    # 2. Finance backend hygiene gate
    backend_gate = (
        repo_root / "Screens" / "Finance" / "Backend" / "checks" / "check_backend_hygiene.py"
    )
    results.append(run_hygiene_gate(backend_gate, "backend hygiene (finance)"))

    # 3. Finance frontend hygiene gate
    frontend_gate = (
        repo_root / "Screens" / "Finance" / "Backend" / "checks" / "check_frontend_hygiene.py"
    )
    results.append(run_hygiene_gate(frontend_gate, "frontend hygiene (finance)"))

    # 4. Structure-docs generator exits 0 (reads only; writes kage-data/structure/)
    generator = repo_root / "Start_Inky" / "generate_structure_docs.py"
    results.append(run_generator_gate(generator, "structure docs generator"))

    # Summary
    print_summary(results)

    # Overall exit code
    if all(status != "FAIL" for _name, status, _code in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())