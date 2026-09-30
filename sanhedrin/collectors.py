"""Source collectors commit complete pages with their resume cursor."""

import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlsplit, parse_qsl, urlunsplit
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from .model import normalize, DataError, utcnow, canonical_json, digest, PROVIDERS
from .html import plain_text
from .net import Client, FetchError, Deferred


def query_url(url, **params):
    p = urlsplit(url)
    query = dict(parse_qsl(p.query))
    query.update({k: v for k, v in params.items() if v is not None})
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query, doseq=True), ""))


def timestamp(value):
    if isinstance(value, (int, float)):
        return int(value)
    return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())


def checked(store, provider, native, state="ok", remote=None, days=7):
    now = datetime.now(timezone.utc)
    store.db.execute(
        "INSERT INTO source_state VALUES(?,?,?,?,?,?) ON CONFLICT(provider,native_id) DO UPDATE SET checked_at=excluded.checked_at,next_check_at=excluded.next_check_at,state=excluded.state,remote_count=excluded.remote_count",
        (
            provider,
            native,
            now.isoformat(),
            (now + timedelta(days=days)).isoformat(),
            state,
            remote,
        ),
    )


def due(store, provider, limit):
    return [
        dict(r)
        for r in store.db.execute(
            "SELECT DISTINCT r.native_id,r.canonical_url FROM records r LEFT JOIN source_state s ON r.provider=s.provider AND r.native_id=s.native_id WHERE r.provider=? AND (s.next_check_at IS NULL OR s.next_check_at<=?) ORDER BY coalesce(s.checked_at,''),r.native_id LIMIT ?",
            (provider, utcnow(), limit),
        )
    ]


def parsed_source(raw, provider, mode="full"):
    q = normalize(
        {
            **raw,
            "provider": provider,
            "source_checked_at": utcnow(),
            "sync_state": "ok",
            "imported_at": utcnow(),
        },
        default_provider=provider,
    )
    if (
        not q["canonical_url"]
        or q["provider"] != provider
        or PROVIDERS.get(urlsplit(q["url"]).hostname) != provider
    ):
        raise DataError(
            "Source item must have an original URL belonging to its provider"
        )
    if raw.get("source_native_id") is not None:
        native = str(raw["source_native_id"])
        if not native.isdigit():
            raise DataError("WordPress native ID must be numeric")
        q["native_id"] = native
        q["identity_method"] = "verified_wordpress_api"
        q["id"] = provider + "-" + native
    if mode == "full" and not q["question"].strip() and not q["answers"]:
        raise DataError("Full collection returned an empty body")
    q["format"] = "html"
    return q


def archive_source(store, raw, origin):
    value = (
        {
            k: v
            for k, v in raw.items()
            if k not in {"source_checked_at", "sync_state", "imported_at"}
        }
        if isinstance(raw, dict)
        else raw
    )
    store.archive(value, origin)


class StackExchange:
    def __init__(self, store, client, config):
        self.s = store
        self.c = client
        self.config = config
        self.counts = Counter()

    def api(self, path, **params):
        data = self.c.get(
            query_url(
                "https://api.stackexchange.com/2.3/" + path,
                site="judaism",
                pagesize=100,
                filter="withbody",
                key=os.getenv(self.config.get("key_env", "STACKEXCHANGE_KEY")) or None,
                **params
            )
        ).json()
        if not isinstance(data, dict) or data.get("error_id"):
            raise FetchError("Stack Exchange API rejected the request")
        if data.get("backoff") is not None:
            self.c.honor_backoff(data["backoff"])
        if data.get("quota_remaining", 0) < self.config.get("quota_reserve", 5):
            raise Deferred("Stack Exchange quota reserve reached")
        if not isinstance(data.get("items"), list) or not isinstance(
            data.get("has_more"), bool
        ):
            raise FetchError("Incomplete Stack Exchange API envelope")
        return data

    def answers(self, ids):
        result = {str(i): [] for i in ids}
        seen = set()
        for page in range(1, self.config.get("answer_max_pages", 100) + 1):
            data = self.api(
                "questions/" + ";".join(map(str, ids)) + "/answers",
                page=page,
                order="asc",
                sort="creation",
            )
            if data["has_more"] and not data["items"]:
                raise DataError("Empty answer page with more results")
            for a in data["items"]:
                aid = str(a.get("answer_id", ""))
                qid = str(a.get("question_id", ""))
                if (
                    not aid.isdigit()
                    or aid in seen
                    or qid not in result
                    or not isinstance(a.get("body"), str)
                    or not isinstance(a.get("is_accepted"), bool)
                ):
                    raise DataError("Invalid or repeated native answer")
                seen.add(aid)
                result[qid].append(
                    {
                        "answer_id": aid,
                        "text": a["body"],
                        "format": "html",
                        "is_accepted": a["is_accepted"],
                        "score": a.get("score"),
                        "author": a.get("owner", {}),
                        "license": a.get("content_license"),
                        "url": "https://judaism.stackexchange.com/a/" + aid,
                        "published_at": a.get("creation_date"),
                        "source_updated_at": a.get("last_activity_date"),
                    }
                )
            if not data["has_more"]:
                return result
        raise Deferred("Answer pagination incomplete; question page was not committed")

    def apply(self, items, cursor_name=None, cursor=None, requested=None):
        if not isinstance(items, list):
            raise DataError("Invalid question page")
        ids = [str(q.get("question_id", "")) for q in items]
        if len(set(ids)) != len(ids) or any(not i.isdigit() for i in ids):
            raise DataError("Invalid or repeated question IDs")
        all_answers = self.answers(ids) if ids else {}
        prepared = []
        for raw, native in zip(items, ids):
            count = raw.get("answer_count")
            if (
                not isinstance(count, int)
                or count < 0
                or len(all_answers[native]) != count
            ):
                raise DataError("Remote answer count mismatch; page not committed")
            if not raw.get("body") or not raw.get("title"):
                raise DataError("Question body or title missing")
            q = parsed_source(
                {
                    "id": "my-" + native,
                    "title": raw["title"],
                    "question": raw["body"],
                    "answers": all_answers[native],
                    "format": "html",
                    "url": raw.get("link")
                    or "https://judaism.stackexchange.com/questions/" + native,
                    "published_at": raw.get("creation_date"),
                    "source_updated_at": raw.get("last_activity_date"),
                    "answer_count_remote": count,
                    "license": raw.get("content_license"),
                    "author": raw.get("owner"),
                    "tags": raw.get("tags", []),
                    "score": raw.get("score"),
                    "views": raw.get("view_count"),
                },
                "miyodeya",
            )
            if q["native_id"] != native:
                raise DataError("API question URL conflicts with native question ID")
            prepared.append((raw, q))
        delta = Counter()
        with self.s.transaction():
            for raw, q in prepared:
                archive_source(self.s, raw, "stackexchange:questions")
                archive_source(
                    self.s, all_answers[q["native_id"]], "stackexchange:answers"
                )
                outcome, public = self.s.upsert(
                    q, mode="source", reason="complete Stack Exchange source check"
                )
                delta[outcome] += len(public)
                age = timestamp(utcnow()) - int(raw.get("last_activity_date") or 0)
                checked(
                    self.s,
                    "miyodeya",
                    q["native_id"],
                    remote=q["answer_count_remote"],
                    days=(
                        1
                        if age < 7 * 86400
                        else 7 if q["answer_count_remote"] == 0 else 30
                    ),
                )
            if requested:
                for native in set(map(str, requested)) - set(ids):
                    checked(self.s, "miyodeya", native, "remote_missing", days=7)
            if cursor_name:
                self.s.set_cursor(cursor_name, cursor)
        self.counts.update(delta)

    def run(self):
        name = "miyodeya:activity"
        state = self.s.cursor(name, {})
        if not state.get("page"):
            end = timestamp(utcnow()) - 60
            start = int(
                state.get("watermark")
                or end - self.config.get("initial_days", 30) * 86400
            ) - self.config.get("overlap_seconds", 172800)
            state = {
                "min": start,
                "max": end,
                "page": 1,
                "watermark": state.get("watermark"),
            }
        for _ in range(self.config.get("max_pages", 20)):
            data = self.api(
                "questions",
                page=state["page"],
                order="asc",
                sort="activity",
                min=state["min"],
                max=state["max"],
            )
            if data["has_more"] and not data["items"]:
                raise DataError("Empty activity page with more results")
            nxt = (
                {**state, "page": state["page"] + 1}
                if data["has_more"]
                else {"watermark": state["max"]}
            )
            self.apply(data["items"], name, nxt)
            state = nxt
            if not data["has_more"]:
                break
        else:
            raise Deferred("Activity pagination continues in the next run")
        candidates = [
            r["native_id"]
            for r in due(self.s, "miyodeya", self.config.get("reconcile_limit", 4000))
            if r["native_id"].isdigit()
        ]
        for offset in range(0, len(candidates), 100):
            ids = candidates[offset : offset + 100]
            data = self.api("questions/" + ";".join(ids), page=1)
            if data["has_more"]:
                raise DataError("Unexpected ID batch pagination")
            self.apply(data["items"], requested=ids)
        return dict(self.counts)


def wordpress_body(body, provider):
    soup = BeautifulSoup(body, "html.parser")
    for n in soup.select(
        "script,style,nav,header,footer,form,.related-posts,.share-buttons"
    ):
        n.decompose()
    text = soup.get_text("\n", strip=True)
    if provider == "din":
        m = re.search(r"שאלה\s*[:：]?\s*(.*?)\s*תשובה\s*[:：]?\s*(.+)", text, re.S)
        if not m:
            raise DataError("DIN question/answer markers missing")
    else:
        m = re.search(r"(.*?)The Aish Rabbi Replies\s*[:：]?\s*(.+)", text, re.S | re.I)
        if not m:
            raise DataError("Aish question/answer markers missing")
    if not m[1].strip() or not m[2].strip():
        raise DataError("Empty publisher question or answer")
    import html

    return "<p>" + html.escape(m[1].strip()).replace("\n", "<br>") + "</p>", [
        {
            "text": "<p>" + html.escape(m[2].strip()).replace("\n", "<br>") + "</p>",
            "format": "html",
        }
    ]


class WordPress:
    def __init__(self, store, client, config, provider):
        self.s = store
        self.c = client
        self.config = config
        self.provider = provider

    def run(self):
        name = self.provider + ":wordpress"
        state = self.s.cursor(name, {})
        if not state.get("page"):
            end = timestamp(utcnow()) - 60
            start = int(
                state.get("watermark")
                or end - self.config.get("initial_days", 30) * 86400
            ) - self.config.get("overlap_seconds", 172800)
            state = {"min": start, "max": end, "page": 1, "fingerprint": None}
        counts = Counter()
        for _ in range(self.config.get("max_pages", 20)):
            iso = lambda v: datetime.fromtimestamp(v, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            fields = "id,link,title,date_gmt,modified_gmt,categories" + (
                ",content" if self.config["mode"] == "full" else ""
            )
            r = self.c.get(
                query_url(
                    self.config["endpoint"],
                    _fields=fields,
                    per_page=self.config.get("per_page", 100),
                    page=state["page"],
                    orderby="modified",
                    order="asc",
                    modified_after=iso(state["min"]),
                    modified_before=iso(state["max"]),
                    status="publish",
                    categories=",".join(map(str, self.config.get("categories", [])))
                    or None,
                ),
                robots=True,
            )
            items = r.json()
            try:
                pages = int(r.headers["X-WP-TotalPages"])
                total = int(r.headers["X-WP-Total"])
            except (KeyError, ValueError, TypeError):
                raise DataError("WordPress pagination headers missing") from None
            if (
                not isinstance(items, list)
                or pages < 0
                or total < 0
                or (not items and total)
            ):
                raise DataError("Invalid WordPress page")
            ids = [str(p.get("id", "")) for p in items]
            fingerprint = digest(ids)
            if (
                len(set(ids)) != len(ids)
                or any(not i.isdigit() for i in ids)
                or (items and fingerprint == state.get("fingerprint"))
            ):
                raise DataError("WordPress page repeated or malformed")
            prepared = []
            for p, native in zip(items, ids):
                modified = timestamp(str(p.get("modified_gmt", "")) + "Z")
                if not state["min"] <= modified <= state["max"]:
                    raise DataError(
                        "WordPress ignored the requested modification window"
                    )
                raw = {
                    "id": self.provider + "-" + native,
                    "source_native_id": native,
                    "title": plain_text(p.get("title", {}).get("rendered", "")),
                    "url": p.get("link"),
                    "published_at": str(p.get("date_gmt", "")) + "Z",
                    "source_updated_at": str(p.get("modified_gmt", "")) + "Z",
                    "kind": "link",
                }
                if self.config["mode"] == "full":
                    raw["question"], raw["answers"] = wordpress_body(
                        p.get("content", {}).get("rendered", ""), self.provider
                    )
                    raw["kind"] = "qa"
                prepared.append(
                    (p, parsed_source(raw, self.provider, self.config["mode"]))
                )
            nxt = (
                {**state, "page": state["page"] + 1, "fingerprint": fingerprint}
                if state["page"] < pages
                else {"watermark": state["max"]}
            )
            with self.s.transaction():
                for p, q in prepared:
                    archive_source(self.s, p, self.provider + ":wordpress")
                    outcome, public = self.s.upsert(
                        q,
                        mode=(
                            "metadata"
                            if self.config["mode"] == "metadata"
                            else "source"
                        ),
                        reason="verified WordPress source",
                    )
                    counts[outcome] += len(public)
                    for pid in public:
                        self.s.alias(self.provider + ":wp:" + q["native_id"], pid)
                    checked(self.s, self.provider, q["native_id"])
                self.s.set_cursor(name, nxt)
            state = nxt
            if "page" not in nxt:
                return dict(counts)
        raise Deferred("WordPress page budget reached; cursor preserved")


def xml_root(body):
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)", body.replace(b"\x00", b""), re.I):
        raise DataError("XML entity declarations are not permitted")
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        raise DataError("Invalid feed XML") from None


def feed_items(body):
    root = xml_root(body)
    items = []
    nodes = root.findall("./channel/item")
    atom = "{http://www.w3.org/2005/Atom}"
    if root.tag == atom + "feed":
        nodes = root.findall(atom + "entry")
    for n in nodes:
        title = n.findtext("title") or n.findtext(atom + "title")
        url = n.findtext("link")
        if not url:
            link = next(
                (
                    v
                    for v in n.findall(atom + "link")
                    if v.get("rel", "alternate") == "alternate"
                ),
                None,
            )
            url = link.get("href") if link is not None else None
        value = (
            n.findtext("pubDate")
            or n.findtext(atom + "published")
            or n.findtext(atom + "updated")
        )
        published = None
        if value:
            try:
                published = parsedate_to_datetime(value).isoformat()
            except (ValueError, TypeError):
                published = value
        if not title or not url:
            raise DataError("Feed item missing title or original URL")
        items.append(
            {
                "title": plain_text(title),
                "url": url.strip(),
                "published_at": published,
                "kind": "link",
            }
        )
    if not nodes:
        raise DataError("Feed contained no recognized items")
    return items


class RSS:
    def __init__(self, store, client, config, provider):
        self.s = store
        self.c = client
        self.config = config
        self.provider = provider

    def run(self):
        counts = Counter()
        endpoints = self.config.get("endpoints") or [self.config["endpoint"]]
        for endpoint in endpoints:
            raw = feed_items(self.c.get(endpoint, robots=True).body)
            prepared = [parsed_source(q, self.provider, "metadata") for q in raw]
            identities = [q["native_id"] for q in prepared]
            if len(set(identities)) != len(identities):
                raise DataError("Feed repeats native identities")
            with self.s.transaction():
                for q in prepared:
                    archive_source(self.s, q, self.provider + ":rss")
                    outcome, ids = self.s.upsert(
                        q, mode="metadata", reason="publisher RSS metadata"
                    )
                    counts[outcome] += len(ids)
                    checked(self.s, self.provider, q["native_id"])
                self.s.set_cursor(
                    self.provider + ":rss:" + digest(endpoint),
                    {
                        "checked_at": utcnow(),
                        "fingerprint": digest(raw),
                        "items": len(raw),
                    },
                )
        return dict(counts)


def yeshiva_page(body, url, mode="metadata"):
    soup = BeautifulSoup(body, "html.parser")
    nodes = []

    def walk(v):
        if isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            nodes.append(v)
            if "@graph" in v:
                walk(v["@graph"])

    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(tag.get_text()))
        except ValueError:
            continue
    page = next((n for n in nodes if n.get("@type") == "QAPage"), {})
    q = page.get("mainEntity", {})
    if isinstance(q, list):
        q = q[0] if q else {}
    title = q.get("name") or (
        soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""
    )
    raw = {
        "title": title,
        "url": url,
        "kind": "link",
        "published_at": q.get("dateCreated") or page.get("datePublished"),
    }
    if mode == "full":
        question = q.get("text") or str(soup.select_one("#questionText") or "")
        answers = q.get("acceptedAnswer") or q.get("suggestedAnswer") or []
        if isinstance(answers, dict):
            answers = [answers]
        raw["question"] = question
        raw["answers"] = [
            {"text": a.get("text", ""), "author": a.get("author"), "format": "html"}
            for a in answers
        ]
        if not raw["answers"] and soup.select_one("#answerText"):
            raw["answers"] = [
                {"text": str(soup.select_one("#answerText")), "format": "html"}
            ]
        raw["kind"] = "qa"
    return raw


class Yeshiva:
    def __init__(self, store, client, config):
        self.s = store
        self.c = client
        self.config = config

    def run(self):
        name = "yeshiva:discovery"
        state = self.s.cursor(name, {"pending": []})
        pending = state.get("pending", [])
        endpoint = self.config.get("discovery_endpoint")
        if endpoint and not pending:
            root = xml_root(self.c.get(endpoint, robots=True).body)
            if root.tag.endswith("urlset"):
                urls = [n.text for n in root.iter() if n.tag.endswith("loc") and n.text]
            else:
                urls = [q["url"] for q in feed_items(ET.tostring(root))]
            pending = sorted(
                {u for u in urls if re.search(r"/ask/\d+(?:$|/)", urlsplit(u).path)}
            )
            for u in pending:
                self.c.validate(u)
            with self.s.transaction():
                self.s.set_cursor(name, {"pending": pending})
        candidates = (
            pending[: self.config.get("reconcile_limit", 10)]
            if pending
            else [
                r["canonical_url"]
                for r in due(self.s, "yeshiva", self.config.get("reconcile_limit", 10))
                if r["canonical_url"]
            ]
        )
        counts = Counter()
        for url in candidates:
            try:
                raw = yeshiva_page(
                    self.c.get(url, robots=True).body, url, self.config["mode"]
                )
                q = parsed_source(raw, "yeshiva", self.config["mode"])
            except FetchError as e:
                if getattr(e, "status", None) not in {404, 410}:
                    raise
                native = re.search(r"/ask/(\d+)", urlsplit(url).path).group(1)
                with self.s.transaction():
                    checked(self.s, "yeshiva", native, "remote_missing", days=30)
                    if url in pending:
                        pending.remove(url)
                        self.s.set_cursor(name, {"pending": pending})
                continue
            with self.s.transaction():
                archive_source(self.s, raw, "yeshiva:source")
                outcome, ids = self.s.upsert(
                    q,
                    mode="metadata" if self.config["mode"] == "metadata" else "source",
                    reason="Yeshiva source check",
                )
                counts[outcome] += len(ids)
                checked(self.s, "yeshiva", q["native_id"])
                if url in pending:
                    pending.remove(url)
                    self.s.set_cursor(name, {"pending": pending})
        return dict(counts)


class JSONFeed:
    """Publisher-provided cursor feed, with optional host-bound authentication."""

    def __init__(self, store, client, config, provider):
        self.s = store
        self.c = client
        self.config = config
        self.provider = provider

    def run(self):
        name = self.provider + ":publisher_feed"
        state = self.s.cursor(name, {})
        url = state.get("next") or query_url(
            self.config["endpoint"],
            **{self.config.get("cursor_parameter", "cursor"): state.get("cursor")}
        )
        seen = set()
        counts = Counter()
        for _ in range(self.config.get("max_pages", 20)):
            self.c.validate(url)
            if url in seen:
                raise DataError("Publisher feed pagination cycle")
            seen.add(url)
            data = self.c.get(url, robots=True).json()
            if (
                data.get("schema") != 1
                or not isinstance(data.get("items"), list)
                or "next" not in data
                or "cursor" not in data
            ):
                raise DataError("Invalid publisher feed envelope")
            nxt = data["next"]
            if nxt is not None:
                if not isinstance(nxt, str):
                    raise DataError("Invalid next feed page")
                self.c.validate(nxt)
                if nxt in seen:
                    raise DataError("Publisher feed pagination cycle")
            prepared = []
            for raw in data["items"]:
                if not isinstance(raw, dict):
                    raise DataError("Invalid publisher feed item")
                if self.config["mode"] == "metadata":
                    raw = {
                        k: v
                        for k, v in raw.items()
                        if k not in {"body", "content", "question", "answer", "answers"}
                    }
                    raw["kind"] = "link"
                prepared.append(parsed_source(raw, self.provider, self.config["mode"]))
            fingerprint = digest([q["native_id"] for q in prepared])
            if len({q["native_id"] for q in prepared}) != len(prepared) or (
                prepared and fingerprint == state.get("fingerprint")
            ):
                raise DataError("Repeated feed page")
            with self.s.transaction():
                for q in prepared:
                    archive_source(self.s, q, self.provider + ":publisher_feed")
                    outcome, ids = self.s.upsert(
                        q,
                        mode=(
                            "metadata"
                            if self.config["mode"] == "metadata"
                            else "source"
                        ),
                        reason="publisher feed",
                    )
                    counts[outcome] += len(ids)
                    checked(self.s, self.provider, q["native_id"])
                state = {
                    "next": nxt,
                    "cursor": data["cursor"],
                    "fingerprint": fingerprint,
                }
                self.s.set_cursor(name, state)
            if nxt is None:
                return dict(counts)
            url = nxt
        raise Deferred("Publisher feed pagination continues next run")


def sync(store, config, *, source=None, client_factory=Client):
    run_id = uuid.uuid4().hex
    report = {"run_id": run_id, "sources": {}}
    started = utcnow()
    with store.transaction():
        store.db.execute(
            "INSERT INTO runs VALUES(?,?,NULL,?,?)",
            (run_id, started, "running", canonical_json(report)),
        )
    for provider, c in config["sources"].items():
        if source and provider != source:
            continue
        if not c["enabled"]:
            report["sources"][provider] = {
                "status": "disabled",
                "reason": c.get("disabled_reason", "Disabled by configuration"),
            }
            continue
        try:
            token = os.getenv(c.get("token_env", "")) if c.get("token_env") else None
            if c.get("token_env") and not token:
                raise Deferred("Publisher access token is not configured")
            client = client_factory(
                c["hosts"],
                budget=c["budget"],
                delay=c.get("delay", 3),
                token=token,
                token_host=urlsplit(c.get("endpoint", "")).hostname,
            )
            adapter = {
                "stackexchange": lambda: StackExchange(store, client, c),
                "wordpress": lambda: WordPress(store, client, c, provider),
                "rss": lambda: RSS(store, client, c, provider),
                "yeshiva": lambda: Yeshiva(store, client, c),
                "json_feed": lambda: JSONFeed(store, client, c, provider),
            }[c["adapter"]]()
            report["sources"][provider] = {
                "status": "ok",
                "counts": adapter.run(),
                "requests": client.used,
            }
        except Deferred as e:
            report["sources"][provider] = {"status": "deferred", "reason": str(e)}
        except (FetchError, DataError) as e:
            report["sources"][provider] = {"status": "error", "reason": str(e)}
        except Exception:
            report["sources"][provider] = {
                "status": "error",
                "reason": "Unexpected collector failure; published content preserved",
            }
    report["status"] = (
        "partial"
        if any(r["status"] in {"error", "deferred"} for r in report["sources"].values())
        else "ok"
    )
    with store.transaction():
        store.db.execute(
            "UPDATE runs SET finished_at=?,status=?,report=? WHERE run_id=?",
            (utcnow(), report["status"], canonical_json(report), run_id),
        )
    return report
