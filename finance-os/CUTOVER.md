# Finance OS cutover — the one manual step

The autonomous build produced `finance-os/` as a parallel tree. It does **not**
touch `Start_Inky/` or the other screens. Cutover — pointing Kage's Finance route
at `finance-os/` and retiring `Screens/Finance/` — is done by a human, because a
blind rewrite of the multi-screen serve file risks breaking Model / Enhancement /
Main Menu.

Do these in order. Each step is reversible via `git checkout`.

## 0. Pre-checks

```sh
cd finance-os
python build.py                       # -> backend/static/index.html + 66 more files
python -m uvicorn backend.main:app --port 8000        # from finance-os/backend: `uvicorn main:app`
# visit http://127.0.0.1:8000/finance  -> Overview renders
# visit http://127.0.0.1:8000/finance/investments  -> deep link resolves (no 404)
python night_worker.py --once         # completes, writes a snapshot + a backup
```

Confirm `.gitignore` keeps `backend/data/` (db, backups, vector_store) and `.env`
out of git — Kage is public, no personal data ever.

## 1. Register finance-os in the shared server

In `Start_Inky/serve_everything_on_one_port.py`, on the Finance route:

- Serve `finance-os/backend` (`main:app`, which is `create_app()` from
  `app_factory`) for `/api/finance/*`.
- Serve `finance-os/backend/static/` (produced by `build.py`) for the Finance UI,
  with an SPA/deep-link fallback (`<path>.html` then `index.html`) — mirror the
  `StaticFiles(..., html=True)` pattern already used for the other screens.
- **Remove** the mount of `Screens/Finance/server_for_finance.py`.

The old `Screens/Finance/` tree stays in git history; it is only unmounted.

## 2. Build step in the launcher

In `Start_Inky/Start_Everything.bat`, before starting the server, run
`python finance-os/build.py` (or document that `build.py` must be run whenever the
Finance frontend changes) so `backend/static/` is fresh.

## 3. Menu target

`Main_Menu/Page/next_app/app/components/NavPanel.tsx` links Finance by the
discovered `address` from `/api/main_menu/navigation`. If the served path stays
`/finance`, no change is needed. If it changed, update the Finance row's target.

## 4. Smoke test

Run `Start_Inky/Start_Everything.bat`. Check:

- Main Menu loads; Model, Finance, Enhancement rows all present and clickable.
- Finance → Overview, Investments, Debt, Tracker, Learning, Settings, Scenario all
  render; a mutation on Tracker updates Overview with no manual refresh.
- The other screens are unaffected.

## 5. Schedule the night worker

Windows Task Scheduler → daily 23:00 IST → `python <repo>/finance-os/night_worker.py`.
(`--once` is for manual runs; scheduled mode also does the weekly gap-only price
refresh on Sundays.)

## Rollback

`git checkout Start_Inky/serve_everything_on_one_port.py Start_Inky/Start_Everything.bat`
restores the old `Screens/Finance/` mount. `finance-os/` can stay in place unused.
