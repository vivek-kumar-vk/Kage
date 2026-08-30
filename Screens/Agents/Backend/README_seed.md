# Agent Deck seed

`seed.py` runs automatically when the Agent Deck backend starts. On a fresh database it seeds the Board and Runs rooms, then seeds ideas either from `Backend/seed_local.json` (if that file exists and parses to a dict with an `ideas` list) or from the built-in generic starter set. The local file is git-ignored and private; commit only `seed_local.example.json`. The seed marks `meta.seeded=yes`, so deleting all idea rows later does not force the starter data back in.
