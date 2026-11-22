"""Unpack a release, verify its contents, and run its actual startup command."""
import argparse
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from build_release import RELEASE_FILES


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def start(app):
    process = subprocess.Popen(
        [sys.executable, "server.py", "--no-browser", "--port", "0"], cwd=app,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        line = lines.get(timeout=15)
        match = re.fullmatch(r"SEEK CL Studio: (http://127\.0\.0\.1:\d+)\s*", line)
        check(match, f"Packaged server did not start: {line}")
        return process, match.group(1)
    except Exception:
        stop(process)
        raise


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    process.stdout.close()


def smoke(archive):
    expected_hash = archive.with_suffix(".zip.sha256").read_text(encoding="utf-8").split()[0]
    check(hashlib.sha256(archive.read_bytes()).hexdigest() == expected_hash, "Archive checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="seek-auto-release-") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.namelist()
            prefix = archive.stem + "/"
            expected = {prefix + name for name in (*RELEASE_FILES, "VERSION", "MANIFEST.json")}
            check(len(members) == len(expected) and set(members) == expected, "Unexpected files in release")
            # Exact allowlist comparison above prevents traversal and private data inclusion.
            bundle.extractall(root)
        app = root / archive.stem
        manifest = json.loads((app / "MANIFEST.json").read_text(encoding="utf-8"))
        check(set(manifest["files"]) == set(RELEASE_FILES) | {"VERSION"}, "Invalid release manifest")
        for relative, checksum in manifest["files"].items():
            check(hashlib.sha256((app / relative).read_bytes()).hexdigest() == checksum, f"Checksum mismatch: {relative}")
        check(not (app / ".local").exists(), "Release includes pre-existing personal data")
        opener = build_opener(ProxyHandler({}))

        def request(base, path, data=None, headers=None):
            if data is not None:
                headers = {"Content-Type": "application/json", **(headers or {})}
            req = Request(base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers or {})
            return opener.open(req, timeout=10)

        process, base = start(app)
        try:
            for path in ("/", "/app.js", "/style.css", "/studio.css"):
                with request(base, path) as response:
                    check(response.status == 200 and len(response.read()) > 0, f"Missing asset: {path}")
                    check(response.headers.get("X-Content-Type-Options") == "nosniff", "Missing security headers")
            with request(base, "/api/state") as response:
                check(json.load(response) == {"jobs": [], "preferences": {}}, "Release did not start with empty data")
            with request(base, "/api/preferences", {"profile": "Synthetic release-check background.",
                         "config": {"api_key": "SYNTHETIC-RELEASE-KEY"}}) as response:
                check(json.load(response)["saved"], "Could not save preferences")
            with request(base, "/api/manual", {"title": "Example Engineer", "company": "Example Studio",
                         "description": "Build and maintain Python services and SQL databases with a small engineering team."}) as response:
                job = json.load(response)["job"]
            with request(base, "/api/status", {"id": job["id"], "status": "Applied"}) as response:
                check(json.load(response)["job"]["application_status"] == "Applied", "Could not update status")
            for path in ("/.local/studio.sqlite3", "/README.md"):
                try:
                    request(base, path).close()
                except HTTPError as error:
                    check(error.code == 404, "Private paths must return 404")
                    error.close()
                else:
                    raise RuntimeError("Private path was served")
            try:
                request(base, "/api/status", {}, {"Origin": "https://example.invalid"}).close()
            except HTTPError as error:
                check(error.code == 403, "Cross-origin request must return 403")
                error.close()
            else:
                raise RuntimeError("Cross-origin request was accepted")
        finally:
            stop(process)
        process, base = start(app)
        try:
            with request(base, "/api/state") as response:
                state = json.load(response)
            check(state["jobs"][0]["application_status"] == "Applied", "Application status did not survive restart")
            check("api_key" not in state["preferences"].get("config", {}), "API key was returned in preferences")
            check(b"SYNTHETIC-RELEASE-KEY" not in (app / ".local/studio.sqlite3").read_bytes(), "API key was written to disk")
        finally:
            stop(process)
    print("PASS: release allowlist, checksums, clean startup, assets, HTTP API, persistence, and private data handling")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    smoke(parser.parse_args().archive.resolve())
