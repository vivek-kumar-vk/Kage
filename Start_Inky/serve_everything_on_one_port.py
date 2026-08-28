"""One address for every screen, so a single ngrok tunnel (or a single
opened port, for any other reason) can reach all of them.

WHY THIS EXISTS
    Every screen already runs on its own port, and that is correct for
    using INKY on this laptop - a browser here can reach 127.0.0.1:8001
    directly. It cannot do that from a phone, or through a tunnel, which
    only ever forwards ONE port. This puts one small router in front of
    all of them.

HOW A REQUEST IS ROUTED
    /api/<screen>/...   that screen's own port, the path unchanged - this
                         is how a page's own root-relative fetch() calls
                         reach it, wherever the page itself was served from
    /<screen>/...        that screen's own port, the "/<screen>" prefix
                         stripped - this is how the page itself and its
                         own static assets are reached
    anything else         Main Menu, unchanged - the shared landing page

    Nothing here names a screen. The routing table is built the same way
    Start_Inky\\start_every_screen.py finds screens to start: by walking
    Screens\\ and reading each one's own settings file.

WHAT THE SCREENS THEMSELVES NEED
    Set INKY_BEHIND_PROXY=1 before starting them (see
    start_everything_behind_one_port.py), so Main Menu's navigation links
    read "/finance/" instead of "http://127.0.0.1:8001/" - see
    Shared_By_All_Screens\\read_screen_settings.py.

RUN IT ON ITS OWN
    (with every screen already running)
    cd <repo root>
    python Start_Inky\\serve_everything_on_one_port.py
    then open http://127.0.0.1:9000
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Main_Menu" / "Backend"))

from Shared_By_All_Screens.read_screen_settings import read_settings, settings_file  # noqa: E402
from find_every_screen import discover                                              # noqa: E402

PROXY_PORT = int(os.environ.get("INKY_PROXY_PORT", "9000"))
TIMEOUT_SECONDS = 30
_HOP_BY_HOP = {"host", "content-length", "transfer-encoding", "connection"}

# Rebind cleanly right after a Ctrl+C restart - without this, Windows
# can hold the old socket long enough to make the next start fail.
ThreadingHTTPServer.allow_reuse_address = True


def routing_table() -> dict[str, tuple[str, int]]:
    """screen folder name (lowercase) -> (host, port). Always has "main_menu"."""
    table: dict[str, tuple[str, int]] = {}

    path = settings_file(PROJECT_ROOT / "Main_Menu")
    if path is not None:
        info = read_settings(path)
        if info["port"] is not None:
            table["main_menu"] = (info["host"], info["port"])

    built, _ = discover()
    for m in built:
        path = settings_file(m.SCREEN_FOLDER)
        if path is None:
            continue
        info = read_settings(path)
        if info["port"] is not None:
            table[m.SCREEN_NAME] = (info["host"], info["port"])

    # The LiteLLM gateway is not a screen (no folder, no settings file),
    # but a phone or a tunnel that can only reach this one port still
    # needs to call it. Give it the same prefix-stripped treatment every
    # screen gets, under /llm/ - so /llm/v1/chat/completions and /llm/ui
    # reach the proxy on its own port. Config, not a name.
    table["llm"] = (
        os.environ.get("LITELLM_HOST", "127.0.0.1"),
        int(os.environ.get("LITELLM_PORT", "8003")),
    )

    return table


def pick_target(path: str, table: dict[str, tuple[str, int]]) -> tuple[tuple[str, int], str]:
    """Which screen a request path belongs to, and the path to forward.

    The first path segment matches case-insensitively. A browser - or a
    person typing an address on a phone - sends /Finance/ just as easily
    as /finance/, while the folders are mixed-case on disk and this
    routing table is lowercase. Only the MATCH is lenient: the forwarded
    path keeps whatever casing arrived, because everything after the
    screen prefix belongs to that screen's own files.
    """
    without_query, _, query = path.partition("?")
    segments = without_query.lstrip("/").split("/")
    first = segments[0].lower() if segments else ""

    if first == "api" and len(segments) > 1 and segments[1].lower() in table:
        return table[segments[1].lower()], path

    if first in table and first != "main_menu":
        remainder = "/" + "/".join(segments[1:])
        if query:
            remainder += "?" + query
        return table[first], remainder

    return table["main_menu"], path


def make_handler(table: dict[str, tuple[str, int]]):
    class Handler(BaseHTTPRequestHandler):
        def _forward(self) -> None:
            (host, port), forward_path = pick_target(self.path, table)
            url = f"http://{host}:{port}{forward_path}"

            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items()
                      if k.lower() not in _HOP_BY_HOP}

            request = urllib.request.Request(url, data=body, headers=headers,
                                             method=self.command)
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
                    self._relay(resp.status, resp.getheaders(), resp.read())
            except urllib.error.HTTPError as e:
                self._relay(e.code, e.headers.items(), e.read())
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                msg = f"{host}:{port} is not answering ({e}). Is that screen running?"
                self._relay(502, [("Content-Type", "text/plain")], msg.encode())

        def _relay(self, status: int, headers, body: bytes) -> None:
            self.send_response(status)
            for k, v in headers:
                if k.lower() not in _HOP_BY_HOP:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self): self._forward()      # noqa: E704
        def do_POST(self): self._forward()     # noqa: E704
        def do_PUT(self): self._forward()      # noqa: E704
        def do_DELETE(self): self._forward()   # noqa: E704
        def do_PATCH(self): self._forward()    # noqa: E704

        def log_message(self, format, *args):  # noqa: A002
            pass   # each screen's own server already logs its requests

    return Handler


def main() -> None:
    table = routing_table()
    if "main_menu" not in table:
        print("Main Menu is not running (or has no settings file) - "
             "nothing to route the fallback path to. Start it first.")
        return

    print("Routing to:")
    for key, (host, port) in sorted(table.items()):
        print(f"  {key:<14} -> http://{host}:{port}")
    print()
    print(f"Listening on http://127.0.0.1:{PROXY_PORT}")
    print("Press Ctrl+C once to stop.")

    server = ThreadingHTTPServer(("0.0.0.0", PROXY_PORT), make_handler(table))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopping")
        server.shutdown()


if __name__ == "__main__":
    main()
