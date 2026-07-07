#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_store.py — zentrales Schreibmodul für die neue Q&A-Struktur.

Neue Fragen werden validiert, bekommen eine stabile ID, werden klassifiziert,
in den offenen Chunk geschrieben und danach in index.json, by-category,
aliases.json und manifest.json eingetragen. responsa.json wird hier nie verändert.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import migrate_qa

SCHEMA = 2
PREFIXES = {"miyodea": "my", "yeshiva": "ye", "upload": "up"}


class ValidationError(ValueError):
    pass


class DuplicateError(ValueError):
    pass


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _classify(title: str, question: str, tags: list[str]):
    """Return category, confidence, needs_review for both old/new classify APIs."""
    result = migrate_qa.classify(title or "", question or "", tags or [])
    if len(result) >= 3:
        return result[0], result[1], bool(result[2])
    raise ValidationError("Klassifizierung lieferte ein ungültiges Ergebnis")


def _entry_year(entry: dict):
    if entry.get("year"):
        return entry.get("year")
    if hasattr(migrate_qa, "year_of"):
        return migrate_qa.year_of(entry)
    if hasattr(migrate_qa, "year_from_date"):
        return migrate_qa.year_from_date(entry.get("date"))
    return None


class QAStore:
    def __init__(self, root=".", base="data/questions", max_per_chunk=None, max_chunk_bytes=None):
        self.root = Path(root).resolve()
        self.base = self.root / base
        self._load_or_init(max_per_chunk, max_chunk_bytes)

    def _read(self, rel, default=None):
        path = self.base / rel
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_or_init(self, max_per_chunk, max_chunk_bytes) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.manifest = self._read("manifest.json")
        if self.manifest is None:
            self.manifest = {
                "schema": SCHEMA,
                "generated": now,
                "total": 0,
                "open_chunk": 1,
                "chunks": 1,
                "max_per_chunk": max_per_chunk or 500,
                "max_chunk_bytes": max_chunk_bytes or 1_500_000,
                "upload_counter": 0,
                "index_files": ["index.json"],
            }
            _atomic_write(self.base / "manifest.json", self.manifest)

        if max_per_chunk:
            self.manifest["max_per_chunk"] = max_per_chunk
        if max_chunk_bytes:
            self.manifest["max_chunk_bytes"] = max_chunk_bytes
        self.manifest.setdefault("upload_counter", 0)
        self.manifest.setdefault("open_chunk", max(1, int(self.manifest.get("chunks", 1))))
        self.manifest.setdefault("chunks", max(1, int(self.manifest.get("open_chunk", 1))))
        self.manifest.setdefault("index_files", ["index.json"])

        self.index = self._read("index.json", {"schema": SCHEMA, "generated": now, "count": 0, "entries": []})
        self.aliases = self._read("aliases.json", {"schema": SCHEMA, "aliases": {}})

        if self._read("categories.json") is None:
            _atomic_write(self.base / "categories.json", {
                "schema": SCHEMA,
                "version": now[:10],
                "default_category": "general",
                "categories": migrate_qa.CATEGORIES,
                "tag_map": migrate_qa.TAG_MAP,
                "legacy_map": migrate_qa.LEGACY_MAP,
            })

        self._cat_ids = {c["id"] for c in self._read("categories.json")["categories"]}
        self._known_ids = {e["id"] for e in self.index.get("entries", [])}

    def _chunk_path(self, no: int) -> Path:
        return self.base / "chunks" / f"qa_{no:04d}.json"

    def _load_chunk(self, no: int):
        path = self._chunk_path(no)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"schema": SCHEMA, "chunk": no, "count": 0, "questions": []}

    @staticmethod
    def _validate(q: dict, require_answer: bool):
        errors = []
        if not str(q.get("question", "")).strip() and not str(q.get("title", "")).strip():
            errors.append("Frage-Text oder Titel erforderlich")

        answers = q.get("answers")
        if answers is None and q.get("answer") is not None:
            answers = [{"text": str(q["answer"]), "accepted": True, "author": None, "score": None}]
        answers = answers or []

        normalized_answers = []
        for answer in answers:
            if isinstance(answer, str):
                answer = {"text": answer, "accepted": False, "author": None, "score": None}
            if str(answer.get("text", "")).strip():
                normalized_answers.append({
                    "text": str(answer["text"]),
                    "accepted": bool(answer.get("accepted", False)),
                    "author": answer.get("author"),
                    "score": answer.get("score"),
                })

        if require_answer and not normalized_answers:
            errors.append("mindestens eine nicht-leere Antwort erforderlich")
        if normalized_answers and not any(a["accepted"] for a in normalized_answers):
            normalized_answers[0]["accepted"] = True

        source = q.get("source", "upload")
        if source not in PREFIXES:
            errors.append(f"unbekannte Quelle '{source}'")

        date = q.get("date")
        if date and not re.match(r"^\d{4}(-\d{2}(-\d{2})?)?$", str(date)):
            errors.append(f"ungültiges Datum '{date}'")

        if errors:
            raise ValidationError("; ".join(errors))
        return normalized_answers, source, q.get("category")

    def _next_upload_sid(self) -> str:
        self.manifest["upload_counter"] = int(self.manifest.get("upload_counter", 0)) + 1
        return f"{datetime.now():%Y}-{self.manifest['upload_counter']:04d}"

    def add_question(self, q: dict, require_answer: bool = True) -> dict:
        answers, source, category_override = self._validate(q, require_answer)
        prefix = PREFIXES[source]
        source_id = str(q.get("source_id") or q.get("id") or "").strip()

        if not source_id:
            if source != "upload":
                raise ValidationError(f"Quelle '{source}' erfordert source_id")
            source_id = self._next_upload_sid()

        qid = f"{prefix}-{source_id}"
        if qid in self._known_ids:
            raise DuplicateError(f"ID existiert bereits: {qid}")
        if source_id in self.aliases.get("aliases", {}) and self.aliases["aliases"][source_id].get("id") == qid:
            raise DuplicateError(f"Alias existiert bereits: {source_id} -> {qid}")

        if category_override:
            if category_override not in self._cat_ids:
                raise ValidationError(f"unbekannte Kategorie '{category_override}'")
            category, confidence, needs_review = category_override, "high", False
        else:
            category, confidence, needs_review = _classify(
                q.get("title", ""), q.get("question", ""), q.get("tags") or []
            )

        entry = {
            "id": qid,
            "legacy": {"source_id": source_id},
            "source": source,
            "title": q.get("title") or str(q.get("question", ""))[:80],
            "question": q.get("question", ""),
            "answers": answers,
            "url": q.get("url"),
            "tags": q.get("tags") or [],
            "date": q.get("date"),
            "category": category,
            "category_confidence": confidence,
        }
        if needs_review:
            entry["needs_review"] = True

        chunk_no = int(self.manifest.get("open_chunk", 1))
        chunk = self._load_chunk(chunk_no)
        chunk_path = self._chunk_path(chunk_no)
        current_size = chunk_path.stat().st_size if chunk_path.exists() else 0
        entry_size = len(json.dumps(entry, ensure_ascii=False).encode("utf-8"))

        if chunk["count"] >= int(self.manifest["max_per_chunk"]) or (
            chunk["count"] and current_size + entry_size > int(self.manifest["max_chunk_bytes"])
        ):
            chunk_no += 1
            chunk = self._load_chunk(chunk_no)
            chunk_path = self._chunk_path(chunk_no)
            self.manifest["open_chunk"] = chunk_no
            self.manifest["chunks"] = max(int(self.manifest.get("chunks", 0)), chunk_no)

        chunk["questions"].append(entry)
        chunk["count"] = len(chunk["questions"])
        self.manifest["chunks"] = max(int(self.manifest.get("chunks", 0)), chunk_no)
        self.manifest["open_chunk"] = chunk_no

        rec = self._index_rec(entry, chunk_no)
        self.index["entries"].append(rec)
        self.index["count"] = len(self.index["entries"])
        self.index["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        bycat = self._read(f"by-category/{category}.json", {
            "schema": SCHEMA,
            "category": category,
            "count": 0,
            "entries": [],
        })
        bycat["entries"].append(rec)
        bycat["count"] = len(bycat["entries"])

        self.aliases.setdefault("aliases", {})[source_id] = {"id": qid, "ch": chunk_no}
        self.manifest["total"] = self.index["count"]

        _atomic_write(chunk_path, chunk)
        _atomic_write(self.base / f"by-category/{category}.json", bycat)
        _atomic_write(self.base / "aliases.json", self.aliases)
        _atomic_write(self.base / "manifest.json", self.manifest)
        _atomic_write(self.base / "index.json", self.index)

        self._known_ids.add(qid)
        return {
            "id": qid,
            "chunk": chunk_no,
            "chunk_file": chunk_path.name,
            "category": category,
            "confidence": confidence,
            "needs_review": needs_review,
        }

    @staticmethod
    def _index_rec(entry: dict, chunk_no: int) -> dict:
        title = entry.get("title") or entry.get("title_he") or entry.get("title_en") or ""
        hebrew_title = bool(re.search(r"[\u0590-\u05FF]", title))
        accepted = next((a for a in entry.get("answers", []) if a.get("accepted")),
                        entry.get("answers", [None])[0] if entry.get("answers") else None)
        rec = {
            "id": entry["id"],
            "t_he": title if hebrew_title else entry.get("title_he", ""),
            "t_en": entry.get("title_en", "") if hebrew_title else title,
            "x": migrate_qa.excerpt(entry.get("question", "")),
            "ax": migrate_qa.excerpt(accepted.get("text", "")) if accepted else "",
            "tg": [str(t).lower() for t in (entry.get("tags") or [])],
            "c": entry["category"],
            "y": _entry_year(entry),
            "ch": chunk_no,
            "s": entry["source"],
        }
        if entry.get("needs_review"):
            rec["r"] = 1
        return rec

    def rebuild_index(self) -> int:
        entries = []
        aliases = {}
        bycat = {cid: [] for cid in self._cat_ids}

        for chunk_file in sorted((self.base / "chunks").glob("qa_*.json")):
            payload = json.loads(chunk_file.read_text(encoding="utf-8"))
            for question in payload.get("questions", []):
                rec = self._index_rec(question, payload["chunk"])
                entries.append(rec)
                bycat.setdefault(question["category"], []).append(rec)
                aliases[question["id"]] = {"id": question["id"], "ch": payload["chunk"]}
                sid = question.get("legacy", {}).get("source_id")
                if sid:
                    aliases[sid] = {"id": question["id"], "ch": payload["chunk"]}
                    if hasattr(migrate_qa, "source_id_number"):
                        aliases[migrate_qa.source_id_number(str(sid))] = {"id": question["id"], "ch": payload["chunk"]}
                num = question.get("legacy", {}).get("number")
                if num is not None:
                    aliases[f"n{num}"] = {"id": question["id"], "ch": payload["chunk"]}
                old_file = question.get("legacy", {}).get("old_file")
                if old_file:
                    aliases[str(old_file)] = {"id": question["id"], "ch": payload["chunk"]}

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.index = {"schema": SCHEMA, "generated": now, "count": len(entries), "entries": entries}
        self.aliases = {"schema": SCHEMA, "aliases": aliases}
        _atomic_write(self.base / "index.json", self.index)
        _atomic_write(self.base / "aliases.json", self.aliases)

        for cid, recs in bycat.items():
            _atomic_write(self.base / f"by-category/{cid}.json", {
                "schema": SCHEMA,
                "category": cid,
                "count": len(recs),
                "entries": recs,
            })

        self.manifest["total"] = len(entries)
        self.manifest["generated"] = now
        _atomic_write(self.base / "manifest.json", self.manifest)
        self._known_ids = {e["id"] for e in entries}
        return len(entries)

    def verify(self) -> list[str]:
        problems = []
        idx = self._read("index.json", {"entries": []}).get("entries", [])
        ids = [e.get("id") for e in idx]
        if len(ids) != len(set(ids)):
            problems.append("doppelte IDs im Index")

        chunk_ids = {}
        for chunk_file in sorted((self.base / "chunks").glob("qa_*.json")):
            payload = json.loads(chunk_file.read_text(encoding="utf-8"))
            if payload.get("count") != len(payload.get("questions", [])):
                problems.append(f"{chunk_file.name}: count stimmt nicht")
            if payload.get("count", 0) > int(self.manifest.get("max_per_chunk", 500)):
                problems.append(f"{chunk_file.name}: über max_per_chunk")
            for question in payload.get("questions", []):
                if question.get("id") in chunk_ids:
                    problems.append(f"ID doppelt in Chunks: {question.get('id')}")
                chunk_ids[question.get("id")] = payload.get("chunk")

        for entry in idx:
            if chunk_ids.get(entry.get("id")) != entry.get("ch"):
                problems.append(f"Index zeigt auf falschen/fehlenden Chunk: {entry.get('id')}")
            if entry.get("c") not in self._cat_ids:
                problems.append(f"unbekannte Kategorie im Index: {entry.get('id')} -> {entry.get('c')}")

        seen = set()
        bycat_total = 0
        for cid in self._cat_ids:
            payload = self._read(f"by-category/{cid}.json")
            if not payload:
                continue
            bycat_total += payload.get("count", 0)
            for entry in payload.get("entries", []):
                if entry.get("id") in seen:
                    problems.append(f"ID in mehreren by-category-Dateien: {entry.get('id')}")
                seen.add(entry.get("id"))
                if entry.get("c") != cid:
                    problems.append(f"falsche Kategorie-Datei: {entry.get('id')}")

        if bycat_total != len(idx):
            problems.append(f"by-category-Summe {bycat_total} != Index {len(idx)}")
        if set(chunk_ids) != set(ids):
            problems.append("Index und Chunks enthalten unterschiedliche ID-Mengen")
        return problems
