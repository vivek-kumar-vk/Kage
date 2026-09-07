"""Generates the three structure documents served by the Storage screen.

WHAT THIS FILE DOES
    Walks the repo (read-only) and writes three JSON files under
    kage-data/structure/: code_structure.json, agent_tree.json and
    data_schema.json. Every value is read from code and databases at
    generation time - nothing is typed by hand, so the documents cannot
    drift from the repo (STORAGE_TAB_SPEC.md section 1, rule 17.5).

    Run by hand:
        .venv\\Scripts\\python Start_Inky\\generate_structure_docs.py
    Run by the Storage screen:
        POST /api/storage/structure/regenerate
    Run by Start_Inky/run_checks.py as a gate that this exits 0.

WHAT THIS FILE MUST NEVER DO
    Edit anything it reads. Invent a value: a field that cannot be read
    from disk is omitted, never guessed (the absent-is-absent rule).
    Touch port settings files, the launcher, or screen discovery - it
    only reads them.

OUTPUTS ARE DISPOSABLE
    The JSON files are derived data (gitignored under /kage-data/);
    deleting kage-data/structure/ and regenerating restores them.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = REPO_ROOT / "Shared_By_All_Screens"
IST = timezone(timedelta(hours=5, minutes=30))
GENERATOR_VERSION = 1

SCREENS_DIR = REPO_ROOT / "Screens"
MENU_BACKEND = REPO_ROOT / "Main_Menu" / "Backend"
AGENTS_DIR = SCREENS_DIR / "Agents" / "AI_Agents"
SPINE_DIR = REPO_ROOT / "kage-data" / "spine"
START_INKY = REPO_ROOT / "Start_Inky"

# The prose below is generator code (one source, reviewed in git), while the
# "present" flag is computed live so a rule whose files vanished shows it.
MARKDOWN_RULES = [
    {"path_pattern": "Shared_By_All_Screens/Current_Numbers/all_current_numbers.md",
     "writer": "read_and_write_numbers.write_state",
     "rule": "key: value per line; blank = None never 0; projection of number_set after K-21"},
    {"path_pattern": "kage-data/library/**/<dated file>",
     "writer": "POST /api/storage/library/<path>",
     "rule": "new dated file per write, never overwrite; /latest reads newest"},
    {"path_pattern": "kage-data/library/books/<slug>/notes/YYYY-MM-DD.md",
     "writer": "owner via PUT /api/storage/doc",
     "rule": "free text; date in filename is the note date"},
    {"path_pattern": "kage-data/library/books/<slug>/insights/YYYY-WW.md",
     "writer": "books_insights (A6)",
     "rule": "BookInsight JSON rendered; first line [Model: …]"},
    {"path_pattern": "kage-data/inbox/pomodoro/*.md",
     "writer": "tray app",
     "rule": "front matter kind/started/ended/minutes/area/label"},
    {"path_pattern": "knowledge/notes/*.md",
     "writer": "research_digester via seam",
     "rule": "must carry **Source:** line; status UNVERIFIED until approved"},
    {"path_pattern": "kage-data/watchdog_audit.md",
     "writer": "watchdog",
     "rule": "regenerated each run from v_watchdog_latest"},
]


def _now() -> str:
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _header() -> dict:
    return {"generated_at": _now(), "generator_version": GENERATOR_VERSION}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _lines(path: Path) -> int:
    return len(_read_text(path).splitlines())


def _backend_dirs() -> list[Path]:
    found = [d / "Backend" for d in sorted(SCREENS_DIR.iterdir()) if (d / "Backend").is_dir()]
    if MENU_BACKEND.is_dir():
        found.append(MENU_BACKEND)
    return found


def _screen_of(backend: Path) -> str:
    if backend == MENU_BACKEND:
        return "main_menu"
    return backend.parent.name.lower()


def _import_tops(tree: ast.AST) -> list[tuple[str, int]]:
    """(top-level module name, line number) for every import in one file."""
    tops = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            tops.append((node.module.split(".")[0], node.lineno))
    return tops


def _shared_names() -> set[str]:
    return {p.stem for p in SHARED_DIR.glob("*.py")} | {"Current_Numbers"}


def _classify_import(top: str, backend: Path) -> str:
    if top in sys.stdlib_module_names:
        return "stdlib"
    if top in _shared_names():
        return "shared"
    if (backend / f"{top}.py").exists() or (backend / top).is_dir():
        return "screen_local"
    return "third_party"


def _load_settings(screen_dir: Path) -> dict:
    """read_settings is the one sanctioned port reader; missing -> None."""
    sys.path.insert(0, str(SHARED_DIR))
    try:
        from read_screen_settings import read_settings, settings_file
    except ImportError:
        return {}
    finally:
        sys.path.pop(0)
    path = settings_file(screen_dir)
    if path is None:
        return {}
    try:
        return read_settings(path)
    except Exception:
        return {}


def _definition(screen_dir: Path) -> dict:
    """SCREEN_NAME / MENU_ORDER / TABS read as literals, never executed."""
    out: dict = {}
    found = sorted(screen_dir.glob("screen_definition_for_*.py"))
    if not found:
        return out
    tree = ast.parse(_read_text(found[0]))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id in {"SCREEN_NAME", "MENU_LABEL"} and isinstance(node.value, ast.Constant):
            out[target.id.lower()] = node.value.value
        elif target.id == "MENU_ORDER" and isinstance(node.value, ast.Constant):
            out["menu_order"] = node.value.value
        elif target.id == "TABS":
            try:
                tabs = ast.literal_eval(node.value)
                out["tabs"] = [t.get("key") for t in tabs if isinstance(t, dict) and t.get("key")]
            except (ValueError, SyntaxError):
                pass
    return out


def _page_kind(page) -> str:
    if page is None:
        return "node"
    text = str(page)
    if "next_app" in text:
        return "next"
    if text.endswith(".html"):
        return "hand-rolled"
    return "node"


def _port_to_screen() -> dict[int, str]:
    ports: dict[int, str] = {}
    for screen_dir in sorted(SCREENS_DIR.iterdir()):
        if not screen_dir.is_dir():
            continue
        settings = _load_settings(screen_dir)
        port = settings.get("port")
        definition = _definition(screen_dir)
        label = definition.get("screen_name") or screen_dir.name.lower()
        if isinstance(port, int):
            ports[port] = label
    return ports


def _scan_ports_literal(text: str):
    for match in re.finditer(r"127\.0\.0\.1:(\d+)", text):
        yield int(match.group(1)), text[: match.start()].count("\n") + 1


def code_structure(repo_root: Path) -> dict:
    doc = _header()
    doc["repo_root"] = str(repo_root)
    shared_names = _shared_names()

    screens, modules, boundaries, violations = [], [], [], []
    shared_imported_by: dict[str, set[str]] = {}
    port_map = _port_to_screen()

    for backend in _backend_dirs():
        screen = _screen_of(backend)
        py_files = sorted(backend.rglob("*.py"))
        py_files = [p for p in py_files if "__pycache__" not in p.parts]

        if screen != "main_menu":
            screen_dir = backend.parent
            settings = _load_settings(screen_dir)
            definition = _definition(screen_dir)
            entry = sorted(backend.glob("server_for_*.py"))
            tests_dir = backend / "tests"
            screens.append({
                "folder": screen_dir.name,
                "screen_name": definition.get("screen_name", screen),
                "port": settings.get("port"),
                "menu_order": definition.get("menu_order"),
                "page_kind": _page_kind(settings.get("page")),
                "backend_py_files": len(py_files),
                "backend_lines": sum(_lines(p) for p in py_files),
                "tests": len(list(tests_dir.glob("test_*.py"))) if tests_dir.is_dir() else 0,
                "tabs": definition.get("tabs", []),
                "entry": entry[0].relative_to(repo_root).as_posix() if entry else None,
            })
        else:
            screens.append({
                "folder": "Main_Menu",
                "screen_name": "main_menu",
                "port": _read_main_menu_port(),
                "menu_order": 0,
                "page_kind": _page_kind(_read_main_menu_page()),
                "backend_py_files": len(py_files),
                "backend_lines": sum(_lines(p) for p in py_files),
                "tests": len(list((backend / "tests").glob("test_*.py")))
                if (backend / "tests").is_dir() else 0,
                "tabs": [],
                "entry": "Main_Menu/Backend/server_for_main_menu.py"
                if (backend / "server_for_main_menu.py").exists() else None,
            })

        for py_file in py_files:
            rel = py_file.relative_to(repo_root).as_posix()
            source = _read_text(py_file)
            imports = {"stdlib": [], "third_party": [], "screen_local": [], "shared": []}
            try:
                tree = ast.parse(source)
            except SyntaxError:
                tree = None
            tops = _import_tops(tree) if tree else []
            for top, _lineno in tops:
                kind = _classify_import(top, backend)
                if top not in imports[kind]:
                    imports[kind].append(top)
            modules.append({
                "path": rel,
                "screen": screen,
                "lines": source.count("\n"),
                "imports": imports,
            })

            for top, lineno in tops:
                if top in shared_names:
                    shared_imported_by.setdefault(top, set()).add(screen)
                if top.startswith(("settings_for_", "server_for_")):
                    other = top.split("_for_")[-1]
                    if other != screen and other != "inky":
                        violations.append({
                            "rule": "screen imports another screen",
                            "evidence": f"{rel}:{lineno} imports {top}",
                        })

            for port, lineno in _scan_ports_literal(source):
                    target = port_map.get(port, f"127.0.0.1:{port}")
                    if target == screen:
                        continue
                    boundaries.append({
                        "from": screen,
                        "to": target,
                        "via": "http",
                        "evidence": f"{rel}:{lineno}",
                    })

    shared = []
    for path in sorted(SHARED_DIR.glob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        shared.append({
            "path": rel,
            "lines": _lines(path),
            "imported_by": sorted(shared_imported_by.get(path.stem, set())),
        })

    launchers = []
    for path in sorted(START_INKY.glob("*.py")):
        launchers.append({
            "path": path.relative_to(repo_root).as_posix(),
            "lines": _lines(path),
        })

    doc["screens"] = screens
    doc["shared"] = shared
    doc["launchers"] = launchers
    doc["modules"] = modules
    doc["boundaries"] = boundaries
    doc["violations"] = violations
    return doc


def _read_main_menu_port():
    settings = _load_settings(REPO_ROOT / "Main_Menu")
    return settings.get("port")


def _read_main_menu_page():
    settings = _load_settings(REPO_ROOT / "Main_Menu")
    return settings.get("page")


def _spine_types() -> dict[str, list[str]]:
    """{event type: required payload keys} parsed from the spine source."""
    source = _read_text(SHARED_DIR / "spine.py")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TYPES" for t in node.targets
        ):
            try:
                return {k: list(v) for k, v in ast.literal_eval(node.value).items()}
            except (ValueError, SyntaxError):
                return {}
    return {}


def agent_tree(repo_root: Path) -> dict:
    doc = _header()

    agents = []
    if AGENTS_DIR.is_dir():
        for folder in sorted(AGENTS_DIR.iterdir()):
            office = folder / "office.json"
            if not (folder.is_dir() and office.exists()):
                continue
            try:
                meta = json.loads(_read_text(office))
            except ValueError:
                meta = {}
            agent = {
                "id": folder.name,
                "folder": folder.relative_to(repo_root).as_posix(),
            }
            for key in ("tier", "department", "task_class", "schema", "max_tokens"):
                if meta.get(key) is not None:
                    agent[key] = meta[key]
            agents.append(agent)

    orchestration: dict = {}
    watchdog = MENU_BACKEND / "watchdog.py"
    if watchdog.exists():
        entry = {"module": watchdog.relative_to(repo_root).as_posix()}
        source = _read_text(watchdog)
        match = re.search(r"INTERVAL_MINUTES\s*=\s*(\d+)", source)
        if match:
            entry["cadence"] = f"every {match.group(1)} min"
        calendar_src = _read_text(MENU_BACKEND / "calendar_pipeline.py")
        if "watchdog" in calendar_src:
            entry["tick"] = "calendar_pipeline.background_loop"
        orchestration["watchdog"] = entry

    omni = SCREENS_DIR / "Agents" / "Backend" / "services" / "omni.py"
    if omni.exists():
        seam = {"module": omni.relative_to(repo_root).as_posix()}
        endpoint = _seam_endpoint(repo_root)
        if endpoint:
            seam["endpoint"] = endpoint
        orchestration["seam"] = seam

    brokers = []
    types = _spine_types()
    if SPINE_DIR.is_dir():
        broker = {
            "name": "spine",
            "path": "kage-data/spine/events_YYYY-MM.jsonl",
            "types": len(types),
        }
        if (SPINE_DIR / "spine.sqlite").exists():
            broker["projection"] = "kage-data/spine/spine.sqlite"
        brokers.append(broker)

    routing_path = SPINE_DIR / "_routing.json"
    default_path = SCREENS_DIR / "Agents" / "Backend" / "routing_default.json"
    source_path = routing_path if routing_path.exists() else default_path
    routing: dict = {"source": source_path.relative_to(repo_root).as_posix()}
    rows = []
    if source_path.exists():
        try:
            data = json.loads(_read_text(source_path))
            for task_class, spec in (data.get("tasks") or {}).items():
                chain = spec.get("chain") if isinstance(spec, dict) else spec
                rows.append({"task_class": task_class, "chain": list(chain or [])})
        except ValueError:
            pass
    routing["rows"] = rows

    doc["agents"] = agents
    doc["orchestration"] = orchestration
    doc["edges"] = []
    doc["brokers"] = brokers
    doc["routing"] = routing
    doc["legacy"] = {
        "agent_folders_present": len([d for d in AGENTS_DIR.iterdir() if d.is_dir()])
        if AGENTS_DIR.is_dir() else 0,
    }
    return doc


def _seam_endpoint(repo_root: Path) -> str | None:
    """POST route whose path mentions llm, with the screen's API prefix."""
    backend = SCREENS_DIR / "Agents" / "Backend"
    prefix = None
    for path in backend.glob("settings_for_*.py"):
        match = re.search(r"API_PREFIX\s*=\s*[\"']([^\"']+)[\"']", _read_text(path))
        if match:
            prefix = match.group(1)
            break
    for path in sorted((backend / "services").glob("*.py")):
        for match in re.finditer(r"@router\.post\(\s*[\"']([^\"']*)[\"']", _read_text(path)):
            route = match.group(1)
            if "llm" in route:
                return f"POST {prefix or '/api/agents'}{route}"
    return None


def _open_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _describe_db(path: Path, repo_root: Path) -> dict:
    entry: dict = {
        "path": path.relative_to(repo_root).as_posix(),
    }
    parts = path.relative_to(repo_root).parts
    entry["screen"] = parts[1].lower() if parts[0] == "Screens" else "storage"
    conn = _open_ro(path)
    try:
        entry["user_version"] = conn.execute("PRAGMA user_version").fetchone()[0]
        tables, views = [], []
        objects = conn.execute(
            "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        view_names = {name for name, kind in objects if kind == "view"}
        for name, _kind in objects:
            if name in view_names:
                views.append(name)
                continue
            try:
                rows = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except sqlite3.Error:
                rows = None
            columns = []
            for _cid, col_name, col_type, notnull, _default, pk in conn.execute(
                f'PRAGMA table_info("{name}")'
            ):
                columns.append({"name": col_name, "type": col_type, "pk": bool(pk), "notnull": bool(notnull)})
            foreign_keys = []
            for _fid, _seq, table, _from, column, _to_update, _to_delete, to_col in conn.execute(
                f'PRAGMA foreign_key_list("{name}")'
            ):
                foreign_keys.append({
                    "column": column,
                    "references": f"{table}.{to_col or 'id'}",
                })
            tables.append({
                "name": name,
                "rows": rows,
                "columns": columns,
                "foreign_keys": foreign_keys,
            })
        entry["tables"] = tables
        if views:
            entry["views"] = views
    finally:
        conn.close()
    return entry


def _db_files(repo_root: Path) -> list[Path]:
    roots = [d for d in (SCREENS_DIR / "*").glob("*/Backend") if d.is_dir()]
    found: dict[str, Path] = {}
    for backend in roots:
        for path in backend.rglob("*"):
            if path.suffix in {".db", ".sqlite"} and "__pycache__" not in path.parts:
                found[path.as_posix()] = path
    kage = repo_root / "kage-data"
    if kage.is_dir():
        for path in kage.rglob("*"):
            if path.suffix in {".db", ".sqlite"}:
                found[path.as_posix()] = path
    return [found[key] for key in sorted(found)]


def data_schema(repo_root: Path) -> dict:
    doc = _header()

    databases = []
    relationships = []
    for path in _db_files(repo_root):
        try:
            entry = _describe_db(path, repo_root)
            databases.append(entry)
            for table in entry.get("tables", []):
                for fk in table.get("foreign_keys", []):
                    relationships.append({
                        "from": f'{entry["screen"]}.{table["name"]}.{fk["column"]}',
                        "to": f'{entry["screen"]}.{fk["references"]}',
                    })
        except sqlite3.Error as exc:
            databases.append({
                "path": path.relative_to(repo_root).as_posix(),
                "screen": path.relative_to(repo_root).parts[1].lower()
                if path.relative_to(repo_root).parts[0] == "Screens" else "storage",
                "error": str(exc),
            })

    spine_events = []
    producers: dict[str, set[str]] = {}
    for backend in _backend_dirs():
        screen = _screen_of(backend)
        for py_file in backend.rglob("*.py"):
            source = _read_text(py_file)
            for match in re.finditer(
                r"emit\(\s*[\"']([a-z_]+)[\"']\s*,\s*[\"']([a-z_]+)[\"']", source
            ):
                producers.setdefault(match.group(2), set()).add(match.group(1))
    for event_type, keys in _spine_types().items():
        spine_events.append({
            "type": event_type,
            "producers": sorted(producers.get(event_type, set())),
            "payload_keys": list(keys),
        })

    markdown_rules = []
    for rule in MARKDOWN_RULES:
        pattern = rule["path_pattern"]
        if "<dated file>" in pattern:
            present = (repo_root / "Shared_By_All_Screens" / "Current_Numbers").is_dir() \
                if "Current_Numbers" in pattern else (repo_root / "kage-data" / "library").is_dir()
        elif "*" in pattern or "**" in pattern:
            base = pattern.split("/")[0]
            present = (repo_root / base).is_dir()
        else:
            present = (repo_root / pattern).exists()
        markdown_rules.append({**rule, "present": bool(present)})

    doc["databases"] = databases
    doc["spine_events"] = spine_events
    doc["markdown_rules"] = markdown_rules
    doc["relationships"] = relationships
    return doc


def generate_all(repo_root: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, builder in (
        ("code_structure", code_structure),
        ("agent_tree", agent_tree),
        ("data_schema", data_schema),
    ):
        doc = builder(repo_root)
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        written[name] = path
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "kage-data" / "structure")
    args = parser.parse_args()
    started = time.time()
    written = generate_all(args.repo_root, args.out_dir)
    seconds = round(time.time() - started, 2)
    for name, path in written.items():
        try:
            shown = path.relative_to(args.repo_root)
        except ValueError:
            shown = path  # --out-dir outside the repo (e.g. a test's tmp dir)
        print(f"wrote {shown} ({name})")
    print(f"done in {seconds}s (limit 10s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
