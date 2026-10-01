"""Save a confirmed GitHub request with optimistic atomic commits and retries."""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sanhedrin.model import DataError, canonical_json, digest
from sanhedrin.store import Store
from sanhedrin.teshuva import compose, render, validate_request, profiles, portrait_rotation, PORTRAIT_ROTATION_PATH, publishable

OPENAI_OWNER = "Moriahise"
RETRYABLE_API_STATES = {"unconfigured", "failed", "disabled", "owner_only", "insufficient", "needs_clarification", "partial"}


def openai_access(request, issue, actor, triggering_actor, repository, enabled):
    """Decide API access from authenticated GitHub metadata, never request fields."""
    if not request.get("use_openai"):
        return ""
    owner = OPENAI_OWNER.casefold()
    identities = (repository.split("/")[0], actor, triggering_actor,
                  issue.get("user", {}).get("login", ""))
    if any(str(login).casefold() != owner for login in identities):
        return "owner_only"
    if enabled != "true":
        return "disabled"
    return ""


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise DataError("Invalid repository")
        self.base = "https://api.github.com/repos/" + repository
        self.token = token

    def request(self, method, path, value=None, optional=False):
        req = urllib.request.Request(self.base + path, method=method,
            data=json.dumps(value).encode() if value is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if optional and error.code == 404:
                return None
            raise

    def content(self, path, ref="main"):
        result = self.request("GET", "/contents/" + quote(path, safe="/") + "?ref=" + quote(ref, safe=""), optional=True)
        if result is None:
            return None
        if result.get("encoding") != "base64":
            raise DataError("Unexpected GitHub content encoding")
        return base64.b64decode(result["content"]).decode("utf-8")


def parse_body(body):
    if not isinstance(body, str) or len(body) > 60000 or "<!-- sanhedrin-teshuva:v1 -->" not in body:
        raise DataError("This is not a Teshuva submission")
    matches = re.findall(r"```json\s*\n(.*?)\n```", body, flags=re.S)
    if len(matches) != 1:
        raise DataError("The request must contain exactly one JSON block")
    return json.loads(matches[0])


def authorized(api, event, actor, repository):
    if actor == repository.split("/")[0]:
        return True
    try:
        result = api.request("GET", "/collaborators/" + quote(actor, safe="") + "/permission", optional=True)
        return bool(result and result.get("permission") in {"admin", "maintain", "write"})
    except urllib.error.HTTPError as error:
        if error.code in {403, 404}:
            return False
        raise


def atomic_save(api, result, request_hash, *, attempts=4, replace_fallback=False, portrait_choices=None, commit_guard=None, expected_existing=False):
    json_path = "Sanhedrin/" + result["id"] + ".json"
    html_path = "Sanhedrin/" + result["id"] + ".html"
    for attempt in range(attempts):
        ref = api.request("GET", "/git/ref/heads/main")
        sha = ref["object"]["sha"]
        existing = api.content(json_path, sha)
        if expected_existing and not existing:
            raise DataError("The saved request was removed during research; no response was restored")
        if commit_guard and not commit_guard():
            raise DataError("The question was changed or closed during research; no response was saved")
        counter = None
        if existing:
            saved = json.loads(existing)
            if saved.get("request_hash") != request_hash or saved.get("id") != result["id"]:
                raise DataError("Saved response identity conflict")
            if not (replace_fallback and (saved.get("answer_version", 0) < 8
                    or saved.get("openai_status") in RETRYABLE_API_STATES)):
                result = saved
            else:
                # Upgrading a saved draft keeps its original portrait and sequence.
                result = {**result, "profile": saved["profile"]}
                if "portrait_sequence" in saved:
                    result["portrait_sequence"] = saved["portrait_sequence"]
        elif result.get("portrait_rotation") == "round_robin":
            if not portrait_choices:
                raise DataError("No portraits available for automatic rotation")
            counter = portrait_rotation(api.content(PORTRAIT_ROTATION_PATH, sha))
            index = counter["next_index"]
            result = {**result, "profile": portrait_choices[index % len(portrait_choices)],
                      "portrait_sequence": index}
            counter["next_index"] = index + 1
        files = {json_path: canonical_json(result) + "\n", html_path: render(result)}
        if counter is not None:
            files[PORTRAIT_ROTATION_PATH] = canonical_json(counter) + "\n"
        if existing and api.content(html_path, sha) == files[html_path]:
            return result, sha, False
        parent = api.request("GET", "/git/commits/" + sha)
        tree = api.request("POST", "/git/trees", {"base_tree": parent["tree"]["sha"], "tree": [
            {"path": p, "mode": "100644", "type": "blob", "content": c} for p, c in files.items()]})
        commit = api.request("POST", "/git/commits", {"message": "Save source-based Teshuva " + result["id"], "tree": tree["sha"], "parents": [sha]})
        try:
            api.request("PATCH", "/git/refs/heads/main", {"sha": commit["sha"], "force": False})
            return result, commit["sha"], True
        except urllib.error.HTTPError as error:
            if error.code not in {409, 422} or attempt == attempts - 1:
                raise
    raise DataError("Repository changed repeatedly; rerun the save workflow")


def save(api, root, store, issue, request, *, api_key="", model="gpt-5.4-mini", api_block_reason="", retry_pending=False, commit_guard=None):
    validated = validate_request(request, root)
    request_hash = digest(validated)
    identity = "teshuva-" + str(issue) + "-" + request_hash[:12]
    existing = api.content("Sanhedrin/" + identity + ".json")
    retry_api = False
    if existing:
        result = json.loads(existing)
        if result.get("request_hash") != request_hash:
            raise DataError("Saved request hash conflict")
        retry_api = bool(validated["use_openai"] and api_key and not api_block_reason
                         and (result.get("answer_version", 0) < 8 and result.get('publication_status') != 'ready'
                              or result.get("openai_status") in RETRYABLE_API_STATES
                              and (result.get("openai_status") not in {"insufficient", "needs_clarification", "partial"} or retry_pending)))
    if not existing or retry_api:
        result = compose(store, root, request, identity=identity, api_key=api_key,
                         model=model, api_block_reason=api_block_reason)
    result, commit, changed = atomic_save(api, result, request_hash, replace_fallback=retry_api,
                                         portrait_choices=profiles(root), commit_guard=commit_guard, expected_existing=bool(existing))
    return {"saved": True, "changed": changed, "id": result["id"], "commit": commit,
            "mode": result["mode"], "openai_status": result["openai_status"],
            "publication_status": result.get("publication_status", "ready" if publishable(result) else "needs_research"),
            "clarification_questions": result.get("clarification_questions", []), "missing_evidence": result.get("missing_evidence", [])}


def main():
    root = Path(__file__).resolve().parents[1]
    repository = os.environ["GITHUB_REPOSITORY"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    actor = os.environ["GITHUB_ACTOR"]
    api = GitHub(repository, os.environ["GH_TOKEN"])
    number = int(os.environ.get("ISSUE_NUMBER") or event.get("issue", {}).get("number") or 0)
    if number < 1:
        raise DataError("A GitHub issue number is required")
    if not authorized(api, event, actor, repository):
        return {"saved": False, "status": "awaiting_repository_approval"}
    issue = api.request("GET", "/issues/" + str(number))
    if issue.get("pull_request") or issue.get("state") != "open" or not issue.get("title", "").startswith("[Teshuva]"):
        raise DataError("Choose an open Teshuva issue")
    request = parse_body(issue.get("body"))
    if event.get("issue") and event["issue"].get("body") != issue["body"]:
        return {"saved": False, "status": "superseded_request"}
    api_block_reason = openai_access(request, issue, actor,
        os.environ.get("GITHUB_TRIGGERING_ACTOR", ""), repository,
        os.environ.get("OPENAI_ENABLED", ""))
    def current_request():
        live = api.request("GET", "/issues/" + str(number))
        return live.get("state") == "open" and live.get("body") == issue.get("body") and live.get("user", {}).get("login") == issue.get("user", {}).get("login")
    with Store(root / ".sanhedrin/library.sqlite") as store:
        result = save(api, root, store, number, request,
                      api_key="" if api_block_reason else os.environ.get("OPENAI_API_KEY", ""),
                      api_block_reason=api_block_reason,
                      model=os.environ.get("OPENAI_MODEL") or "gpt-5.4-mini",
                      retry_pending=os.environ.get("RETRY_RESEARCH") == "true", commit_guard=current_request)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write("saved=true\npublication_status=" + result["publication_status"] + "\n")
    marker = "<!-- sanhedrin-teshuva-result -->"
    if result["publication_status"] in {"ready", "partial", "sources"}:
        label = {"ready": "The checked answer is saved.", "partial": "The supported answer is saved. Open points are listed separately on the answer page.", "sources": "Relevant original answer texts are saved with links to their full sources."}[result['publication_status']]
        body = marker + "\n" + label + "\n\n[Answer](https://shekhina.org/Sanhedrin/" + result["id"] + ".html) · [HTML](https://github.com/" + repository + "/blob/main/Sanhedrin/" + result["id"] + ".html) · [JSON](https://github.com/" + repository + "/blob/main/Sanhedrin/" + result["id"] + ".json).\n\nThe site may take a few minutes to publish."
    else:
        body = marker + "\nNo sufficiently relevant answer text has been found yet. The question and research record are saved.\n\n[Research record](https://github.com/" + repository + "/blob/main/Sanhedrin/" + result["id"] + ".json)."
        if result["clarification_questions"]:
            body += "\n\nPlease add these details to the question and submit the updated request:\n" + "\n".join("- " + q for q in result["clarification_questions"])
        if result["missing_evidence"]:
            body += "\n\nEvidence still needed:\n" + "\n".join("- " + q for q in result["missing_evidence"])
        body += "\n\nMoriahise can enable external research in the request or run Save Teshuva with retry_research to repeat an authorized research attempt."
    try:
        comments = api.request("GET", "/issues/" + str(number) + "/comments?per_page=100")
        old = next((c for c in comments if marker in (c.get("body") or "") and c.get("user", {}).get("login") == "github-actions[bot]"), None)
        if old:
            if old["body"] != body:
                api.request("PATCH", "/issues/comments/" + str(old["id"]), {"body": body})
        else:
            api.request("POST", "/issues/" + str(number) + "/comments", {"body": body})
    except urllib.error.HTTPError:
        result["comment_status"] = "unavailable"
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as error:
        # Never print HTTP bodies, request payloads or credentials.
        print(json.dumps({"saved": False, "error": type(error).__name__}))
        sys.exit(1)
