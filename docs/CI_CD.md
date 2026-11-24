# CI/CD and release guide

The app runs on your own computer. Continuous delivery produces a tested ZIP that you can download and run with Python; it does not require a hosting account, personal API key, or deployment secret.

## Automated checks

The **CI and delivery** workflow runs on pushes to `main`, pull requests targeting `main`, `v*` tags, and manual requests from the Actions tab.

| Stage | Checks |
| --- | --- |
| Backend | Unit tests, the SEEK endpoint regression, and a real HTTP round trip against a synthetic AI provider on Windows and Linux with Python 3.10 and 3.14 |
| Browser | Headless Chrome journeys on Windows and Linux using Node.js 22; importing, setup, generation, editing, copying, revisions, persistence, key handling, and desktop/mobile layouts |
| Package | Build an explicit allowlist of runtime files, generate checksums, unpack into a temporary directory, launch the actual server, and verify assets, HTTP operations, persistence, and private data handling on Windows and Linux |
| Delivery | Upload the ZIP and SHA-256 file as Actions artifacts after all backend and browser checks pass |
| Release | On version tags, publish the tested ZIP and checksum to GitHub Releases after both package checks pass |

Tests and packages contain synthetic fixtures only. Runtime and test dependencies use the Python standard library; the browser check uses the Node.js standard library and the Chrome installation provided on hosted runners. Official Actions are pinned to commit SHAs, with Dependabot configured to propose updates. Only the release job has repository write permission.

## Download a development build

Open **Actions → CI and delivery → a successful run → Artifacts** and download `release-ubuntu-latest` or `release-windows-latest`. Unzip the Actions artifact, then unzip the `seek-auto-dev-<commit>.zip` inside it. From that directory, run:

```sh
python server.py
```

Python 3.10+ must be installed. The archive includes `VERSION`, a per-file `MANIFEST.json`, and a separate archive checksum. Development artifacts expire after 14 days; versioned GitHub Release assets remain available until removed.

## Publish a version

Choose an unused semantic version after the commit on `main` passes CI. The second release is `v0.2.0`; use the next unused version for future releases. Update the source `VERSION`, the UI version label, README, and CHANGELOG, then add detailed notes at `docs/releases/<tag>.md` before tagging:

```sh
git switch main
git pull --ff-only
git tag v0.2.0
git push origin v0.2.0
```

The tag starts a fresh run of the full workflow. A failed test blocks release publication. The release job downloads the previously tested archive, verifies its checksum, creates a draft with the assets, and publishes it after upload succeeds. If `docs/releases/<tag>.md` exists in the tagged commit, that file supplies the Release description; otherwise GitHub generates the notes.

Do not move a published tag. For fixes, publish the next version. If publication fails after creating a draft, inspect or remove the incomplete draft before rerunning the release job; the workflow deliberately does not overwrite an existing release.

To roll back locally, stop the app and run an older release from a separate directory. Keep the current `.local/` folder as a backup; do not overwrite a newer database with an older one. The workflow does not modify anyone's local data.

## Run checks locally

```sh
python -m unittest discover -v
node --check static/app.js
node browser_check.mjs
python scripts/build_release.py --version v0.2.0
python scripts/smoke_release.py dist/seek-auto-v0.2.0.zip
```

Set `CHROME_PATH` if Chrome is not found automatically. All test data is isolated from the normal application database. Release construction uses an explicit list of runtime files and shipped documentation, so adding a runtime asset or a new release document also requires updating `RELEASE_FILES` in `scripts/build_release.py`.

## Check external integrations

Normal CI runs offline against fake job responses and a local synthetic AI endpoint. That keeps builds repeatable and avoids provider charges.

For a live SEEK diagnostic, choose **Run workflow**, enable **live_seek**, and run it on `main`, or run locally:

```sh
python scripts/check_live_seek.py
```

This performs one public search and one detail request without personal information or API credentials. A failure can reflect endpoint changes, rate limits, network restrictions, or an expired listing. It does not block the ordinary offline delivery jobs.

Live model output and account access require your own API provider, key, and model. In the app, use **Test connection**, then generate a letter from a non-sensitive example and review it. CI does not spend API credit or claim to verify live model quality.
