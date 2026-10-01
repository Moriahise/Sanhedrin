"""Deterministic static export with complete search and bounded catalogue reads."""

import base64
import hashlib
import html
import json
import re
import shutil
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from bs4 import BeautifulSoup
from .html import sanitize, plain_text, tokens
from .model import DataError, canonical_json, digest
from .migrate import sha256_file

PAGE_SIZE = 64
STOPWORDS = set(
    "a an and are as at be been but by for from had has have he her his i if in into is it its of on or our she so than that the their them then there these they this to was we were what when where which who why will with you your".split()
)
SYNONYMS = {
    "shabbos": "shabbat",
    "shabat": "shabbat",
    "halakha": "halacha",
    "halakhah": "halacha",
    "halachah": "halacha",
    "tanakh": "tanach",
    "mitzvah": "mitzva",
    "berakhah": "beracha",
    "berakha": "beracha",
    "bracha": "beracha",
    "brachah": "beracha",
}
RENDER_VERSION = sha256_file(Path(__file__).with_name("html.py"))


def shard(key, length=3):
    return hashlib.sha256(key.encode()).hexdigest()[:length]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def year(value):
    text = str(value or "")
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else ""


def rendered(store, text, fmt, base_url=""):
    key = digest([RENDER_VERSION, text, fmt, base_url])
    cached = store.db.execute(
        "SELECT html,text FROM render_cache WHERE hash=?", (key,)
    ).fetchone()
    if cached:
        return cached[0], cached[1]
    safe = (
        sanitize(text, fmt, base_url)
        if fmt != "plain"
        else "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"
    )
    plain = plain_text(safe)
    store.db.execute("INSERT INTO render_cache VALUES(?,?,?)", (key, safe, plain))
    return safe, plain


def safe_document(root, relative, output, expected_sha):
    source = (root / relative).resolve()
    if not source.is_relative_to(root.resolve()) or sha256_file(source) != expected_sha:
        raise DataError("Document changed after migration: " + relative)
    soup = BeautifulSoup(source.read_text(), "html.parser")
    title = soup.title.get_text() if soup.title else Path(relative).stem
    content = soup.select_one(".content") or soup.find("main") or soup.body or soup
    images = []
    depth = len(Path(relative).parts) - 1
    for img in content.find_all("img"):
        src = str(img.get("src") or "")
        if not src.startswith("data:image/") or ";base64," not in src:
            continue
        mime, encoded = src.split(";base64,", 1)
        ext = {
            "data:image/png": "png",
            "data:image/jpeg": "jpg",
            "data:image/gif": "gif",
            "data:image/webp": "webp",
        }.get(mime)
        if not ext:
            continue
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise DataError("Invalid document image: " + relative) from None
        signatures = {
            "png": data.startswith(b"\x89PNG\r\n\x1a\n"),
            "jpg": data.startswith(b"\xff\xd8\xff"),
            "gif": data.startswith((b"GIF87a", b"GIF89a")),
            "webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        }
        if not signatures[ext] or len(data) > 15_000_000:
            raise DataError("Unsafe document image: " + relative)
        name = hashlib.sha256(data).hexdigest() + "." + ext
        asset = output / "document-images" / name
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(data)
        marker = f"SANHEDRINIMAGE{len(images)}PLACEHOLDER"
        prefix = "../" * depth
        images.append(
            (
                marker,
                '<img src="'
                + prefix
                + "document-images/"
                + name
                + '" alt="'
                + html.escape(str(img.get("alt") or ""), quote=True)
                + '" loading="lazy">',
            )
        )
        img.replace_with(marker)
    for node in content.select("[data-tooltip]"):
        node.append(" [" + str(node.get("data-tooltip")) + "]")
    safe = sanitize(str(content))
    for marker, tag in images:
        safe = safe.replace(marker, tag)
    prefix = "../" * depth
    page = (
        '<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'self\'; img-src \'self\'; base-uri \'none\'; form-action \'none\'"><title>'
        + html.escape(title)
        + '</title><link rel="stylesheet" href="'
        + prefix
        + 'catalog.css"></head><body class="document-page"><main class="reading"><a href="'
        + prefix
        + 'index.html">← Sanhedrin</a><article dir="auto">'
        + safe
        + "</article></main></body></html>"
    )
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page)


def build(store, root, destination, *, max_bytes=900_000_000):
    root = root.resolve()
    destination = destination.resolve()
    if destination == root or root.is_relative_to(destination):
        raise DataError("Export must use a separate directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".sanhedrin-build-", dir=destination.parent))
    previous = None
    try:
        result = _build(store, root, stage, max_bytes)
        if destination.exists():
            previous = destination.with_name(".sanhedrin-previous-" + uuid.uuid4().hex)
            destination.rename(previous)
        stage.rename(destination)
        return result
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        if previous and previous.exists() and not destination.exists():
            previous.rename(destination)
        raise


def _build(store, root, out, max_bytes):
    from .retrieval import search_text
    search_config = json.loads((root / "config/teshuva-search.json").read_text())
    hebrew_roots = {term for group in search_config["groups"] for term in group if re.search(r"[\u0590-\u05ff]", term)}
    logical = store.logical_hash()
    release = "v1-" + digest([logical, RENDER_VERSION, sha256_file(__file__), sha256_file(root / "config/teshuva-search.json")])[:24]
    dataout = out / "releases" / release
    for name in (
        "index.html",
        "qa.html",
        "catalog.css",
        "catalog-app.js",
        "catalog-data.js",
        "status.html",
        "status-app.js",
        "teshuva.html",
        "teshuva.css",
        "teshuva-app.js",
        "teshuva-data.js",
    ):
        shutil.copyfile(root / "web" / name, out / name)
    if (root / "CNAME").exists():
        shutil.copyfile(root / "CNAME", out / "CNAME")
    (out / ".nojekyll").write_text("")
    records = list(store.records())
    if not records:
        raise DataError("Refusing an empty catalogue export")
    records.sort(
        key=lambda q: (q.get("imported_at") or q.get("published_at") or "", q["id"]),
        reverse=True,
    )
    id_to_n = {q["id"]: n for n, q in enumerate(records)}
    facets = defaultdict(lambda: defaultdict(list))
    locators = defaultdict(dict)
    metadata = []
    postings = defaultdict(lambda: defaultdict(list))
    counts = Counter()
    max_content = 0
    with store.transaction():
        for n, q in enumerate(records):
            pid = q["id"]
            url = q.get("url") or ""
            question_html, question_text = rendered(
                store, q.get("question", ""), q.get("format", "html"), url
            )
            answers = []
            answer_texts = []
            for a in q.get("answers", []):
                safe, text = rendered(
                    store,
                    a.get("text", ""),
                    a.get("format", q.get("format", "html")),
                    url,
                )
                answers.append(
                    {k: v for k, v in a.items() if k not in {"text", "body", "answer"}}
                    | {"html": safe}
                )
                answer_texts.append(text)
            language = q.get("language") or (
                "he" if any("\u0590" <= c <= "\u05ff" for c in q["title"]) else "en"
            )
            card = {
                "id": pid,
                "n": n,
                "title": plain_text(q["title"]),
                "title_he": q.get("title_he", ""),
                "title_en": q.get("title_en", ""),
                "excerpt": (question_text or " ".join(answer_texts))[:220],
                "provider": q["provider"],
                "category": q["category"],
                "kind": q["kind"],
                "language": language,
                "published_at": q.get("published_at"),
                "imported_at": q.get("imported_at"),
                "answers": len(answers),
                "needs_review": bool(q.get("needs_review")),
                "url": url,
                "quality_status": q.get("quality_status"),
                "has_evidence": any(len(t) >= 25 for t in answer_texts) or (q["kind"] in {"article", "document"} and len(question_text) >= 25),
            }
            if q.get("document_path"):
                card["document_path"] = q["document_path"]
            metadata.append(card)
            content = {
                **card,
                "question_html": question_html,
                "answers": answers,
                "tags": q.get("tags", []),
                "saved_at": q.get("saved_at"),
                "legacy_date": q.get("legacy_date"),
                "source_checked_at": q.get("source_checked_at"),
                "sync_state": q.get("sync_state", "not_checked"),
                "answer_count_remote": q.get("answer_count_remote"),
                "license": q.get("license"),
                "author": q.get("author"),
                "author_url": q.get("author_url"),
                "import_charges": q.get("import_charges", []),
            }
            file = f"content/{shard(pid,2)}/{hashlib.sha256(pid.encode()).hexdigest()}.json"
            write_json(dataout / file, content)
            max_content = max(max_content, (dataout / file).stat().st_size)
            locators[shard(pid, 2)][pid] = {"n": n, "file": file}
            for field in ("provider", "category", "kind", "language"):
                facets[field][card[field]].append(n)
            if card["has_evidence"]:
                facets["evidence"]["available"].append(n)
            if year(card["published_at"]):
                facets["published_year"][year(card["published_at"])].append(n)
            import_years = {year(q.get("imported_at")), year(q.get("saved_at"))} | {
                year(c.get("date")) for c in q.get("import_charges", [])
            }
            for value in sorted(import_years - {""}):
                facets["imported_year"][value].append(n)
            status = (
                "remote_unanswered"
                if q.get("answer_count_remote") == 0 and q.get("sync_state") == "ok"
                else "answered" if answers else "local_missing"
            )
            facets["answer_status"][status].append(n)
            if card["needs_review"]:
                facets["review"]["needed"].append(n)
            weighted = Counter()
            for text, weight in [
                (q["title"], 8),
                (" ".join(q.get("tags", [])), 6),
                (question_text, 3),
                (" ".join(answer_texts), 1),
            ]:
                for word in set(tokens(text)) | set(tokens(search_text(text))):
                    word = SYNONYMS.get(word, word)
                    if len(word) >= 2 and word not in STOPWORDS:
                        weighted[word] += weight
            for word in list(weighted):
                for prefix_size in (1, 2):
                    if len(word) > prefix_size + 2 and all(c in "והשבלמכ" for c in word[:prefix_size]) and word[prefix_size:] in hebrew_roots:
                        weighted[word[prefix_size:]] = max(weighted[word[prefix_size:]], weighted[word])
            for word, weight in weighted.items():
                postings[shard(word)][word].extend((n, weight))
            counts[q["provider"]] += 1
    for page in range(0, len(metadata), PAGE_SIZE):
        write_json(
            dataout / f"catalog/pages/{page//PAGE_SIZE:05d}.json",
            metadata[page : page + PAGE_SIZE],
        )
    for key, value in locators.items():
        write_json(dataout / f"catalog/locator/{key}.json", value)
    alias_parts = defaultdict(dict)
    for alias, context, pid in store.db.execute(
        "SELECT alias,context,public_id FROM aliases ORDER BY alias,context,public_id"
    ):
        if pid not in id_to_n:
            raise DataError("Alias points outside export")
        key = alias + "\0" + context
        alias_parts[shard(key)].setdefault(key, []).append(pid)
    for key, value in alias_parts.items():
        write_json(dataout / f"catalog/aliases/{key}.json", value)
    facet_manifest = {}
    for field, values in facets.items():
        facet_manifest[field] = {}
        for value, ids in values.items():
            file = f"catalog/facets/{field}/{shard(value,16)}.json"
            write_json(dataout / file, ids)
            facet_manifest[field][value] = {"count": len(ids), "file": file}
    for key, value in postings.items():
        write_json(dataout / f"search/{key}.json", value)
    for q in records:
        if q.get("document_path"):
            safe_document(root, q["document_path"], out, q["document_sha256"])
    from .teshuva import publish_assets

    teshuva_assets = publish_assets(root, out)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    if size > max_bytes:
        raise DataError(f"Export size {size} exceeds budget {max_bytes}")
    manifest = {
        "schema": 1,
        "release": release,
        "total": len(metadata),
        "baseline_total": store.db.execute("SELECT count(*) FROM baseline").fetchone()[
            0
        ],
        "page_size": PAGE_SIZE,
        "provider_counts": dict(counts),
        "facets": facet_manifest,
        "stopwords": sorted(STOPWORDS),
        "synonyms": SYNONYMS,
        "locator_shard_chars": 2,
        "alias_shard_chars": 3,
        "search_shard_chars": 3,
        "documents": sum(q["kind"] == "document" for q in records),
        "max_content_bytes": max_content,
        "max_search_shard_bytes": max(
            (p.stat().st_size for p in (dataout / "search").glob("*.json")), default=0
        ),
        "uncompressed_site_bytes": size,
        "data_base": f"releases/{release}/",
        "teshuva": teshuva_assets,
    }
    write_json(out / "catalog/manifest.json", manifest)
    write_json(
        dataout / "catalog/documents.json",
        [m for m in metadata if m["kind"] == "document"],
    )
    from .status import status

    write_json(out / "status.json", status(store))
    checksums = {
        p.relative_to(out).as_posix(): sha256_file(p)
        for p in out.rglob("*")
        if p.is_file()
    }
    write_json(
        out / "release.json",
        {"schema": 1, "release": release, "logical_hash": logical, "files": checksums},
    )
    if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) > max_bytes:
        raise DataError("Final export exceeds byte budget")
    return manifest


def verify_export(path):
    release = json.loads((path / "release.json").read_text())
    manifest = json.loads((path / "catalog/manifest.json").read_text())
    for relative, sha in release["files"].items():
        p = (path / relative).resolve()
        if (
            not p.is_relative_to(path.resolve())
            or not p.is_file()
            or sha256_file(p) != sha
        ):
            raise DataError("Export checksum mismatch: " + relative)
    cards = [
        c
        for p in sorted((path / manifest["data_base"] / "catalog/pages").glob("*.json"))
        for c in json.loads(p.read_text())
    ]
    if len(cards) != manifest["total"] or len({c["id"] for c in cards}) != len(cards):
        raise DataError("Export cardinality mismatch")
    return {
        "total": len(cards),
        "verified_files": len(release["files"]),
        "release": release["release"],
    }
