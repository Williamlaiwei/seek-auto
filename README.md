# SEEK Auto — CL Studio

A local, interactive workspace for turning SEEK job listings and your own experience into cover letters. Import a job, review the match, draft a letter, and copy it into your application on SEEK.

Built with the Python standard library and plain HTML, CSS, and JavaScript. No Python packages, Node.js installation, or build step are needed to run the app.

## Quick start

Requires **Python 3.10+**.

```sh
git clone https://github.com/Williamlaiwei/seek-auto.git
cd seek-auto
python server.py
```

Your browser opens at **http://127.0.0.1:8766**. On Windows, you can also double-click `start-web.cmd`.

```sh
python server.py --port 8767   # Use another port
python server.py --no-browser # Start without opening a browser
```

## Features

- Import a SEEK job URL, search Australian listings, or paste a job description manually.
- Save your background, real examples, job preferences, and writing style locally.
- Generate an English cover letter with a brief fit summary, strengths, gaps, and facts to confirm.
- Edit drafts with automatic local saving, request revisions, and retain previous letter versions.
- Copy a letter, open the listing on SEEK, and track the application status.
- Filter, rank, and export your saved jobs in a responsive desktop and mobile interface.

## Write your first letter

1. Open **My profile & API**. Add your background, strengths, and real examples. You can paste text or import a `.txt`, `.md`, or `.json` file.
2. Optionally add job preferences, example letters, and writing instructions. Examples guide tone and structure; your background supplies the facts.
3. Select your AI provider, enter a model ID available to your account, and enter your API key. Use **Test connection** to check the configuration.
4. Paste a SEEK job URL or use **Paste a description instead** if importing fails.
5. Select the job and choose **Generate cover letter**. Review the assessment and check any facts that need confirmation.
6. Edit or revise the letter, copy it, and open **Apply on SEEK** to submit it yourself.

Generating a letter or opening SEEK does not submit an application. Set the local status to **Applied** after you submit it.

## AI configuration

The app uses APIs that support **Chat Completions and JSON mode**. Provider presets include OpenAI, DeepSeek, Gemini's compatible endpoint, and a custom endpoint. Enter a model supported by your provider and account.

Remote endpoints require HTTPS. A compatible local model server may use HTTP on localhost and does not require an API key. Generating a letter and assessing a job send your supplied background and the selected job description to the configured provider.

An AI API account and any associated usage costs are separate from running this app.

## Local data and privacy

- Jobs, drafts, background text, and preferences are stored in `.local/studio.sqlite3`.
- Your API key stays in page memory and is sent to the local backend for API requests. It is not saved to the database or browser storage; enter it again after reloading the page.
- The server binds to `127.0.0.1` and checks request origins. It is intended for use on your own computer.
- `.local/`, environment files, databases, personal documents, and generated artifacts are excluded by `.gitignore`.
- The source contains no saved user profiles, CVs, letters, API credentials, or browser sessions. Tests use synthetic data and fake AI responses.

## Development

Run the backend tests:

```sh
python -m unittest -v
```

Check frontend syntax if Node.js is installed:

```sh
node --check static/app.js
```

The optional browser integration check requires **Node.js 22+ and Chrome**:

```sh
node browser_check.mjs
```

Set `CHROME_PATH` if Chrome is installed elsewhere. The check uses a disposable database and fake job/AI responses to verify importing, generation, editing, clipboard copying, revisions, persistence, key handling, and desktop/mobile layouts. Screenshots and browser profiles are written under the ignored `.local/` directory. These checks do not validate live AI quality or current SEEK endpoint availability.

## Project structure

```text
server.py          Local HTTP server, AI requests, and SQLite storage
seek_search.py     SEEK search and job-detail utility
static/            Interactive HTML, CSS, and JavaScript interface
test_server.py     Backend tests with synthetic fixtures
browser_check.mjs  Optional Chrome integration check
start-web.cmd      Windows launcher
LICENSE            MIT license and original copyright notices
```

## Limitations

SEEK discovery uses unofficial endpoints that may change, reject requests, or return incomplete data. Paste the job description when import is unavailable. Fit scores are suggestions based on the information supplied, not predictions of hiring outcomes. Review every generated claim before submitting.

## Credits and license

The SEEK search utility is adapted from [RinaldoG/ai-job-search-au](https://github.com/RinaldoG/ai-job-search-au), which builds on [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search). Its search approach references [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider).

This repository publishes the standalone CL Studio app. The imported job-search framework is not bundled.

Released under the [MIT License](LICENSE). Original copyright notices are retained.
