"""Build a deterministic, allowlisted source bundle without local user data."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_FILES = (
    ".gitignore", "LICENSE", "README.md", "CHANGELOG.md", "docs/CI_CD.md",
    "docs/releases/v0.2.0.md", "server.py", "seek_search.py", "start-web.cmd",
    "static/index.html", "static/app.js", "static/style.css", "static/studio.css",
)


def build(version, output):
    if not re.fullmatch(r"v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?|dev-[0-9a-f]{7,40}", version):
        raise ValueError("Use a semantic version such as v0.1.0 or dev-<commit SHA>.")
    output.mkdir(parents=True, exist_ok=True)
    name = f"seek-auto-{version}"
    files = {}
    for relative in RELEASE_FILES:
        source = ROOT / relative
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f"Refusing to package a symlink or external file: {relative}")
        files[relative] = source.read_bytes()
    files["VERSION"] = (version + "\n").encode()
    manifest = {"version": version, "files": {path: hashlib.sha256(data).hexdigest() for path, data in files.items()}}
    files["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    archive = output / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, data in sorted(files.items()):
            entry = zipfile.ZipInfo(f"{name}/{relative}", date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, data)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    print(archive)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.version, args.output)
