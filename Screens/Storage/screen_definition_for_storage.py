"""What the Storage screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Nothing in
    Main_Menu or Start_Inky is edited to make this appear - they walk
    the Screens folder and find it (CLAUDE.md Rule 17).

WHAT IS BEHIND IT
    The repo's one local-disk storage seam (D11.5): every screen's own
    persistence funnels through read_doc/write_doc/list_docs/delete_doc/
    search, addressed by logical path, backed by plain files under
    KAGE_DATA_DIR - outside this repo (Rule 7), never Google Drive (D11.5
    dropped that transport). A hybrid (keyword + dense) RAG layer sits on
    top of the same files, and an append-only trader-decisions ledger
    stub lives here too, unbuilt beyond that ledger.

    This screen is a complete independent component - it imports nothing
    from Shared_By_All_Screens/ or Shared_By_All_Agents/, and reaches
    into no other screen's code. Consumers (Finance, Learning, ...) call
    this seam over HTTP, like any other cross-screen call.
"""

SCREEN_NAME = "storage"
MENU_LABEL = "STORAGE"
MENU_ORDER = 8

# One tab. This screen shows the seam's own health - not a document editor.
TABS = [
    {"key": "status", "label": "Status", "endpoint": "/api/storage/status"},
]
