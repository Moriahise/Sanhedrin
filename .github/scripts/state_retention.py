"""Retain the seven newest verified automatic database releases in this repository."""
import json
import os
import re
import subprocess
import time

KEEP = 7
TAG = re.compile(r"sanhedrin-state-\d{8}T\d{12}Z-([0-9a-f]{12})")
ASSETS = {"library.sqlite.gz", "snapshot.json"}


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def automatic(release):
    return (
        TAG.fullmatch(release["tag_name"])
        and release["author"]["login"] == "github-actions[bot]"
        and not release["draft"] and not release["prerelease"]
        and not release.get("immutable", False)
        and {asset["name"] for asset in release["assets"]} == ASSETS
    )


def verify(repo, release):
    tag = release["tag_name"]
    assets = {a["name"]: a for a in release["assets"]}
    meta = json.loads(gh("release", "download", tag, "--repo", repo,
                         "--pattern", "snapshot.json", "--output", "-"))
    packed = assets["library.sqlite.gz"]
    digest = meta.get("compressed_sha256", "")
    if not (all(a["state"] == "uploaded" for a in assets.values())
            and meta.get("schema") == 1
            and meta.get("total", 0) >= meta.get("baseline_total", 0) >= 63051
            and re.fullmatch("[0-9a-f]{64}", digest)
            and packed["digest"] == "sha256:" + digest
            and packed["size"] == meta["compressed_bytes"] > 0
            and meta["logical_hash"][:12] == TAG.fullmatch(tag)[1]):
        raise ValueError("Retained backup failed verification: " + tag)
    print("Verified backup:", tag, flush=True)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    if repo not in {"Moriahise/Sanhedrin", "Moriahise/Beit-Din-Gadol"}:
        raise SystemExit("Unexpected repository")
    pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"))
    releases = sorted((r for page in pages for r in page if automatic(r)),
                      key=lambda r: r["tag_name"], reverse=True)
    protected, old = releases[:KEEP], releases[KEEP:]
    for release in protected:
        verify(repo, release)
    for release in old:
        tag = release["tag_name"]
        print("Removing old automatic backup:", tag, flush=True)
        gh("release", "delete", tag, "--repo", repo, "--cleanup-tag", "--yes")
        time.sleep(4)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
        print(f"Verified and kept {len(protected)} automatic backups. Removed {len(old)} older backups.", file=out)


if __name__ == "__main__":
    main()
