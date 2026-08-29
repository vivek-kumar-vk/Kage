# Learning seed data

This screen seeds SQLite data through `Backend/seed.py`.

## Two-tier seeding

1. If `Backend/seed_local.json` exists, `seed.py` uses it.
2. Otherwise, `seed.py` uses built-in generic rows.

`Backend/seed_local.json` is gitignored. Do not commit personal data.

## Create your local seed file

Copy the example:

```bash
cp Backend/seed_local.example.json Backend/seed_local.json
```

Then edit `Backend/seed_local.json`.

## Date helper

Use:

```json
"@today"
```

for any date field that should become the current IST date when seeding.

## Topic and card links

For cards and reviews, prefer:

```json
"topic_index": 1
"card_index": 1
```

These are 1-based indexes into the seeded `topics` and `cards` arrays.

You may also use explicit DB ids:

```json
"topic_id": 12
"card_id": 7
```

But explicit ids are less portable.

## Important

Seeding only inserts into a table when that table is empty.
If you want to reseed, delete or move `Backend/learning.db` first.
