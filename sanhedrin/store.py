"""Transactional SQLite records, originals, revisions, aliases and durable cursors."""

import copy
import json
import sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from .model import DataError, canonical_json, digest, utcnow, content_fingerprint

DDL = """
CREATE TABLE IF NOT EXISTS records(public_id TEXT PRIMARY KEY,provider TEXT NOT NULL,native_id TEXT NOT NULL,canonical_url TEXT NOT NULL,payload TEXT NOT NULL,content_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS records_identity ON records(provider,native_id);
CREATE INDEX IF NOT EXISTS records_url ON records(provider,canonical_url);
CREATE TABLE IF NOT EXISTS baseline(public_id TEXT PRIMARY KEY,payload TEXT NOT NULL,body_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,public_id TEXT NOT NULL REFERENCES records(public_id),payload TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS revisions_public ON revisions(public_id,id);
CREATE TABLE IF NOT EXISTS aliases(alias TEXT NOT NULL,context TEXT NOT NULL DEFAULT '',public_id TEXT NOT NULL REFERENCES records(public_id),PRIMARY KEY(alias,context,public_id));
CREATE INDEX IF NOT EXISTS aliases_key ON aliases(alias,context);
CREATE TABLE IF NOT EXISTS imports(path TEXT PRIMARY KEY,sha256 TEXT NOT NULL,report TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS raw_records(hash TEXT PRIMARY KEY,origin TEXT NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quarantine(origin TEXT NOT NULL,ordinal INTEGER NOT NULL,reason TEXT NOT NULL,raw_hash TEXT NOT NULL,PRIMARY KEY(origin,ordinal,raw_hash));
CREATE TABLE IF NOT EXISTS source_state(provider TEXT NOT NULL,native_id TEXT NOT NULL,checked_at TEXT,next_check_at TEXT,state TEXT,remote_count INTEGER,PRIMARY KEY(provider,native_id));
CREATE TABLE IF NOT EXISTS cursors(name TEXT PRIMARY KEY,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,report TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS render_cache(hash TEXT PRIMARY KEY,html TEXT NOT NULL,text TEXT NOT NULL);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        if self.db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            raise DataError("Unsupported database schema")
        self.db.executescript(DDL)
        self.db.execute("PRAGMA user_version=1")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        if self.db.in_transaction:
            raise RuntimeError("Nested transactions are not supported")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def get(self, pid):
        r = self.db.execute(
            "SELECT payload FROM records WHERE public_id=?", (pid,)
        ).fetchone()
        return json.loads(r[0]) if r else None

    def count(self):
        return self.db.execute("SELECT count(*) FROM records").fetchone()[0]

    def records(self):
        for r in self.db.execute("SELECT payload FROM records ORDER BY public_id"):
            yield json.loads(r[0])

    def find(self, q):
        rows = self.db.execute(
            "SELECT payload FROM records WHERE provider=? AND native_id=?",
            (q["provider"], q["native_id"]),
        ).fetchall()
        if not rows and q.get("canonical_url"):
            rows = self.db.execute(
                "SELECT payload FROM records WHERE provider=? AND canonical_url=?",
                (q["provider"], q["canonical_url"]),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def archive(self, raw, origin):
        h = digest(raw)
        self.db.execute(
            "INSERT OR IGNORE INTO raw_records VALUES(?,?,?)",
            (h, origin, canonical_json(raw)),
        )
        return h

    def alias(self, alias, pid, context=""):
        if alias:
            self.db.execute(
                "INSERT OR IGNORE INTO aliases VALUES(?,?,?)",
                (str(alias), str(context or ""), pid),
            )

    def resolve(self, alias, context=""):
        if self.get(alias) and not context:
            return [alias]
        rows = self.db.execute(
            "SELECT DISTINCT public_id FROM aliases WHERE alias=? AND context=? ORDER BY public_id",
            (alias, context),
        ).fetchall()
        if not rows and context:
            rows = self.db.execute(
                "SELECT DISTINCT public_id FROM aliases WHERE alias=? AND context='' ORDER BY public_id",
                (alias,),
            ).fetchall()
        return [r[0] for r in rows]

    def insert(self, q, *, baseline=None):
        q = copy.deepcopy(q)
        if self.get(q["id"]):
            raise DataError("Public ID collision: " + q["id"])
        self.db.execute(
            "INSERT INTO records VALUES(?,?,?,?,?,?)",
            (
                q["id"],
                q["provider"],
                q["native_id"],
                q.get("canonical_url", ""),
                canonical_json(q),
                digest(q),
            ),
        )
        self.alias(q["id"], q["id"])
        self.alias(q["provider"] + ":" + q["native_id"], q["id"])
        if (
            q["provider"] in {"miyodeya", "yeshiva", "chabad"}
            and q["native_id"].isdigit()
        ):
            self.alias(q["native_id"], q["id"])
        if baseline is not None:
            self.db.execute(
                "INSERT INTO baseline VALUES(?,?,?)",
                (q["id"], canonical_json(baseline), content_fingerprint(baseline)),
            )
        return q["id"]

    def update(self, old, new, reason):
        if new["id"] != old["id"] or new["provider"] != old["provider"]:
            raise DataError("Updates cannot change public ID or provider")
        if canonical_json(old) == canonical_json(new):
            return False
        observed = {"source_checked_at", "sync_state"}
        if {k: v for k, v in old.items() if k not in observed} != {
            k: v for k, v in new.items() if k not in observed
        }:
            self.db.execute(
                "INSERT INTO revisions(public_id,payload,reason,created_at) VALUES(?,?,?,?)",
                (old["id"], canonical_json(old), reason, utcnow()),
            )
        self.db.execute(
            "UPDATE records SET native_id=?,canonical_url=?,payload=?,content_hash=? WHERE public_id=?",
            (
                new["native_id"],
                new.get("canonical_url", ""),
                canonical_json(new),
                digest(new),
                new["id"],
            ),
        )
        return True

    def upsert(self, q, *, mode="enrich", reason="import"):
        if mode not in {"enrich", "source", "metadata"}:
            raise DataError("Unknown upsert mode")
        existing = self.find(q)
        if not existing:
            q = copy.deepcopy(q)
            if self.get(q["id"]):
                q["id"] += (
                    "-"
                    + digest([q["provider"], q["native_id"], q.get("canonical_url")])[
                        :10
                    ]
                )
            self.insert(q)
            return "inserted", [q["id"]]
        changed = False
        ids = []
        for old in existing:
            ids.append(old["id"])
            new = copy.deepcopy(old)
            if q.get("identity_method") == "verified_wordpress_api":
                new["native_id"] = q["native_id"]
                new["identity_method"] = q["identity_method"]
            if mode == "metadata":
                for key in (
                    "title",
                    "url",
                    "canonical_url",
                    "published_at",
                    "source_updated_at",
                    "source_native_id",
                    "source_checked_at",
                    "sync_state",
                ):
                    if q.get(key) is not None:
                        new[key] = copy.deepcopy(q[key])
            elif mode == "source":
                for key in (
                    "title",
                    "question",
                    "format",
                    "url",
                    "canonical_url",
                    "published_at",
                    "source_updated_at",
                    "tags",
                    "score",
                    "views",
                    "license",
                    "author",
                    "author_url",
                    "source_native_id",
                    "answer_count_remote",
                    "source_checked_at",
                    "sync_state",
                    "kind",
                ):
                    if key in q and q[key] is not None:
                        new[key] = copy.deepcopy(q[key])
                new["answers"] = merge_answers(
                    old.get("answers", []), q.get("answers", [])
                )
                new["answer_count_local"] = len(new["answers"])
                new.pop("quality_status", None)
            else:
                for key in (
                    "published_at",
                    "saved_at",
                    "imported_at",
                    "provider_domain",
                    "kind",
                ):
                    if not new.get(key) and q.get(key):
                        new[key] = copy.deepcopy(q[key])
                if q.get("kind") == "article" and q["provider"] in {"chabad", "aish"}:
                    new["kind"] = "article"
                if not new.get("question") and q.get("question"):
                    new["question"] = q["question"]
                if not new.get("answers") and q.get("answers"):
                    new["answers"] = copy.deepcopy(q["answers"])
                    new["answer_count_local"] = len(new["answers"])
            if self.update(old, new, reason):
                changed = True
            self.alias(new["provider"] + ":" + new["native_id"], old["id"])
        return ("updated" if changed else "unchanged"), ids

    def cursor(self, name, default=None):
        r = self.db.execute(
            "SELECT payload FROM cursors WHERE name=?", (name,)
        ).fetchone()
        return json.loads(r[0]) if r else default

    def set_cursor(self, name, value):
        self.db.execute(
            "INSERT INTO cursors VALUES(?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload",
            (name, canonical_json(value)),
        )

    def logical_hash(self):
        import hashlib

        h = hashlib.sha256()
        for r in self.db.execute(
            "SELECT public_id,content_hash FROM records ORDER BY public_id"
        ):
            h.update((r[0] + "\0" + r[1] + "\n").encode())
        for r in self.db.execute(
            "SELECT alias,context,public_id FROM aliases ORDER BY alias,context,public_id"
        ):
            h.update(canonical_json(list(r)).encode())
        return h.hexdigest()

    def verify(self):
        def retained(original, candidate):
            if original.get("question") and original["question"] != candidate.get(
                "question"
            ):
                return False
            before = Counter(
                a.get("text", "") for a in original.get("answers", []) if a.get("text")
            )
            after = Counter(
                a.get("text", "") for a in candidate.get("answers", []) if a.get("text")
            )
            return not (before - after)

        errors = []
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            errors.append("SQLite integrity failure")
        if self.db.execute("PRAGMA foreign_key_check").fetchall():
            errors.append("Foreign key failure")
        for r in self.db.execute(
            "SELECT public_id,provider,native_id,canonical_url,payload,content_hash FROM records"
        ):
            payload = json.loads(r["payload"])
            if digest(payload) != r["content_hash"]:
                errors.append("Record payload hash mismatch: " + r["public_id"])
            if (
                payload.get("id"),
                payload.get("provider"),
                payload.get("native_id"),
                payload.get("canonical_url", ""),
            ) != (r["public_id"], r["provider"], r["native_id"], r["canonical_url"]):
                errors.append("Record identity columns mismatch: " + r["public_id"])
        for r in self.db.execute("SELECT public_id,payload,body_hash FROM baseline"):
            original = json.loads(r[1])
            current = self.get(r[0])
            if not current:
                errors.append("Baseline ID missing: " + r[0])
            if content_fingerprint(original) != r[2]:
                errors.append("Baseline corrupted: " + r[0])
            if current and not retained(original, current):
                if not any(
                    retained(original, json.loads(v[0]))
                    for v in self.db.execute(
                        "SELECT payload FROM revisions WHERE public_id=?", (r[0],)
                    )
                ):
                    errors.append("Published body lost without revision: " + r[0])
        return errors

    def backup(self, target):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(target)
        try:
            self.db.backup(db)
        finally:
            db.close()


def merge_answers(old, incoming):
    from .html import plain_text, sanitize

    def equivalent(a):
        return (
            plain_text(sanitize(a.get("text", ""), "markdown"))
            if a.get("format") == "markdown"
            else plain_text(a.get("text", ""))
        )

    result = copy.deepcopy(old)
    for a in incoming:
        aid = str(a.get("answer_id") or "")
        match = next(
            (
                i
                for i, v in enumerate(result)
                if aid and str(v.get("answer_id") or "") == aid
            ),
            None,
        )
        if match is None:
            text = equivalent(a)
            candidates = [
                i
                for i, v in enumerate(result)
                if not v.get("answer_id") and equivalent(v) == text and text
            ]
            if len(candidates) == 1:
                match = candidates[0]
        if match is None:
            result.append(copy.deepcopy(a))
        else:
            result[match] = {**result[match], **copy.deepcopy(a)}
    if any(a.get("answer_id") for a in incoming):
        for a in result:
            if not a.get("answer_id"):
                a["legacy_unmatched"] = True
    return result
