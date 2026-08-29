import json
from datetime import datetime, timezone, timedelta

import settings_for_learning as cfg
from db import connect

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%Y-%m-%d")

GENERIC = {
    "topics": [
        {
            "name": "Learn Docker networking",
            "stack_area": "core",
            "track": "A",
            "status": "learning",
            "position": 1,
            "progress": 0.3,
            "target_date": "@today",
            "source_doc": None,
            "group": "core"
        },
        {
            "name": "Kubernetes probes",
            "stack_area": "drip",
            "track": "A",
            "status": "todo",
            "position": 2,
            "progress": 0.0,
            "target_date": None,
            "source_doc": None,
            "group": "drip"
        },
        {
            "name": "Rust ownership",
            "stack_area": "capture",
            "track": "B",
            "status": "todo",
            "position": 1,
            "progress": 0.0,
            "target_date": None,
            "source_doc": None,
            "group": "capture"
        }
    ],
    "week_plans": [
        {
            "week_start": "@today",
            "focus_a": "Docker networking basics",
            "focus_b": "Rust syntax",
            "note": "Keep sessions under 45 mins"
        }
    ],
    "cards": [
        {
            "topic_index": 1,
            "front": "What is the default Docker network driver?",
            "part1": "bridge",
            "part2": "host",
            "part3": "none",
            "part4": "overlay",
            "part5": "macvlan",
            "tag": "core",
            "tether": "docker-net"
        },
        {
            "topic_index": 2,
            "front": "What are Kubernetes liveness probes for?",
            "part1": "Detect deadlocks",
            "part2": "Restart failing containers",
            "part3": "Do not fix slow startup",
            "part4": "Different from readiness",
            "part5": "Configure initialDelaySeconds",
            "tag": "drip",
            "tether": "k8s-probes"
        },
        {
            "topic_index": 3,
            "front": "What does Rust ownership prevent?",
            "part1": "Data races",
            "part2": "Use-after-free",
            "part3": "Double free",
            "part4": "Iterator invalidation",
            "part5": "Memory leaks are still possible",
            "tag": "capture",
            "tether": "rust-ownership"
        }
    ],
    "reviews": [
        {
            "card_index": 1,
            "due_date": "@today",
            "ease": 2.5,
            "status": "active"
        },
        {
            "card_index": 2,
            "due_date": "@today",
            "ease": 2.5,
            "status": "active"
        },
        {
            "card_index": 3,
            "due_date": "@today",
            "ease": 2.5,
            "status": "active"
        }
    ]
}


def _date(value, default=None):
    if value == "@today":
        return TODAY
    if value is None or value == "":
        return default
    return str(value)


def _int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _load_seed_data():
    path = cfg.HERE / "seed_local.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return GENERIC


def _insert_topics(c, topics):
    topic_ids = []
    for t in topics:
        cur = c.execute(
            'INSERT INTO topics (name, stack_area, status, track, position, progress, target_date, source_doc, "group") '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t.get("name"),
                t.get("stack_area", "core"),
                t.get("status", "todo"),
                t.get("track", "A"),
                _int(t.get("position"), 0),
                _float(t.get("progress"), 0.0),
                _date(t.get("target_date"), None),
                t.get("source_doc"),
                t.get("group"),
            ),
        )
        topic_ids.append(cur.lastrowid)
    return topic_ids


def _insert_week_plans(c, plans):
    for p in plans:
        c.execute(
            "INSERT INTO week_plans (week_start, focus_a, focus_b, note) VALUES (?, ?, ?, ?)",
            (
                _date(p.get("week_start"), TODAY),
                p.get("focus_a"),
                p.get("focus_b"),
                p.get("note"),
            ),
        )


def _insert_cards(c, cards, topic_ids):
    card_ids = []
    for card in cards:
        topic_id = card.get("topic_id")
        if not topic_id and card.get("topic_index"):
            idx = _int(card.get("topic_index"), 1) - 1
            if 0 <= idx < len(topic_ids):
                topic_id = topic_ids[idx]

        cur = c.execute(
            "INSERT INTO cards (topic_id, front, part1, part2, part3, part4, part5, tag, tether) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                topic_id,
                card.get("front"),
                card.get("part1", ""),
                card.get("part2", ""),
                card.get("part3", ""),
                card.get("part4", ""),
                card.get("part5", ""),
                card.get("tag", "core"),
                card.get("tether"),
            ),
        )
        card_ids.append(cur.lastrowid)
    return card_ids


def _insert_reviews(c, reviews, card_ids):
    for r in reviews:
        card_id = r.get("card_id")
        if not card_id and r.get("card_index"):
            idx = _int(r.get("card_index"), 1) - 1
            if 0 <= idx < len(card_ids):
                card_id = card_ids[idx]

        if card_id is None:
            continue

        c.execute(
            "INSERT INTO reviews (card_id, due_date, ease, status) VALUES (?, ?, ?, ?)",
            (
                card_id,
                _date(r.get("due_date"), TODAY),
                _float(r.get("ease"), 2.5),
                r.get("status", "active"),
            ),
        )


def run():
    data = _load_seed_data()

    with connect() as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM topics")
        if c.fetchone()[0] == 0:
            topic_ids = _insert_topics(c, data.get("topics", []))
        else:
            topic_ids = [row["id"] for row in c.execute("SELECT id FROM topics ORDER BY id").fetchall()]

        c.execute("SELECT COUNT(*) FROM week_plans")
        if c.fetchone()[0] == 0:
            _insert_week_plans(c, data.get("week_plans", []))

        c.execute("SELECT COUNT(*) FROM cards")
        if c.fetchone()[0] == 0:
            card_ids = _insert_cards(c, data.get("cards", []), topic_ids)
        else:
            card_ids = [row["id"] for row in c.execute("SELECT id FROM cards ORDER BY id").fetchall()]

        c.execute("SELECT COUNT(*) FROM reviews")
        if c.fetchone()[0] == 0:
            _insert_reviews(c, data.get("reviews", []), card_ids)
