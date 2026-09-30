import json
from pathlib import Path
from urllib.parse import urlsplit
from .model import DataError


def load_config(path):
    value = json.loads(Path(path).read_text())
    if value.get("schema") != 1 or not isinstance(value.get("sources"), dict):
        raise DataError("Invalid source configuration")
    for provider, c in value["sources"].items():
        if provider not in {"miyodeya", "yeshiva", "din", "aish", "chabad"}:
            raise DataError("Unknown configured provider")
        if c.get("mode") not in {"metadata", "full"} or c.get("adapter") not in {
            "stackexchange",
            "wordpress",
            "rss",
            "yeshiva",
            "json_feed",
        }:
            raise DataError("Invalid adapter or collection mode")
        if not isinstance(c.get("enabled"), bool) or not c.get("hosts"):
            raise DataError("Source requires hosts and enabled flag")
        if not isinstance(c.get("budget"), int) or not 1 <= c["budget"] <= 1000:
            raise DataError("Invalid request budget")
        if (
            c["enabled"]
            and c["adapter"] in {"rss", "wordpress", "json_feed"}
            and not c.get("endpoint")
        ):
            raise DataError("Enabled adapter needs a verified endpoint")
        if c["mode"] == "full" and not c.get("permission_reference"):
            raise DataError("Full-text collection requires a permission reference")
        if c.get("endpoint"):
            u = urlsplit(c["endpoint"])
            if u.scheme != "https" or u.hostname not in c["hosts"]:
                raise DataError("Endpoint must use an allowlisted HTTPS host")
    return value
