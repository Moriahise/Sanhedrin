"""GitHub Release state persists independently of ephemeral runners and caches."""

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .model import DataError
from .snapshot import restore

TAG = re.compile(r"^sanhedrin-state-\d{8}T\d{12}Z-[a-f0-9]{12}$")


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode:
        raise DataError("GitHub Release operation failed; existing state preserved")
    return r.stdout


def latest(repo):
    candidates = []
    for page in range(1, 101):
        entries = json.loads(
            gh("api", f"repos/{repo}/releases?per_page=100&page={page}")
        )
        if not isinstance(entries, list):
            raise DataError("Invalid GitHub release list")
        candidates.extend(
            r
            for r in entries
            if not r.get("draft") and TAG.fullmatch(r.get("tag_name", ""))
        )
        if len(entries) < 100:
            break
    else:
        raise DataError(
            "Release pagination exceeded; refusing a partial state selection"
        )
    return max(candidates, key=lambda r: r["tag_name"]) if candidates else None


def restore_release(repo, directory, destination, *, minimum_total=63051):
    release = latest(repo)
    if not release:
        return {"status": "bootstrap", "reason": "No persisted state release exists"}
    assets = {a["name"] for a in release.get("assets", [])}
    if not {"library.sqlite.gz", "snapshot.json"} <= assets:
        raise DataError("Latest state release is incomplete; refusing a baseline reset")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    gh(
        "release",
        "download",
        release["tag_name"],
        "--repo",
        repo,
        "--dir",
        str(directory),
        "--pattern",
        "library.sqlite.gz",
        "--pattern",
        "snapshot.json",
        "--clobber",
    )
    metadata = restore(directory, destination, minimum_total=minimum_total)
    return {"status": "restored", "tag": release["tag_name"], **metadata}


def publish_snapshot(repo, directory, commit):
    directory = Path(directory)
    meta = json.loads((directory / "snapshot.json").read_text())
    packed = directory / "library.sqlite.gz"
    if packed.stat().st_size >= 2 * 1024**3:
        raise DataError("Snapshot exceeds the GitHub Release per-asset limit")
    from .migrate import sha256_file

    if sha256_file(packed) != meta["compressed_sha256"]:
        raise DataError("Snapshot changed before publication")
    tag = (
        "sanhedrin-state-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + meta["logical_hash"][:12]
    )
    gh(
        "release",
        "create",
        tag,
        str(packed),
        str(directory / "snapshot.json"),
        "--repo",
        repo,
        "--target",
        commit,
        "--latest=false",
        "--title",
        "Sanhedrin durable state " + tag,
        "--notes",
        f"Verified state with {meta['total']} records; restore validates both checksums, public IDs and revisions.",
    )
    return {"tag": tag, "total": meta["total"]}
