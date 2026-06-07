# Release Guide — Publishing to PyPI

This is the operator runbook for cutting a release of `jsm-ticket-analytics-export`
to PyPI. It assumes you have a PyPI account and an API token.

---

## ⛔ STOP — pre-flight sanitization blockers

**This is a PUBLIC package built against an enterprise system. Do not upload until
every item below is resolved.** The packaging, README, and dev docs are already
sanitized (synthetic placeholders only). The remaining leaks live in **source and
tests**, which are outside the release-prep edit scope and must be fixed by the
code owner before the package is published.

> The artifacts currently in `dist/` were built for validation only and **still
> contain the real instance** (via `config.py`). Re-run `uv build` *after* the
> fixes below, then upload the freshly built artifacts.

### 1. `config.py` — real instance hardcoded ⚠️ CRITICAL (functionality + leak)

`config.py:5-6` ships the real internal Jira host and project key **inside the
wheel**:

```python
JIRA_INSTANCE = "https://servicedesk.inside-box.net"   # employer identifier — must not ship
PROJECT_KEY = "IT"
```

This is both a data leak **and** a functionality blocker: anyone who `pip install`s
the package gets a tool hardcoded to an instance they can't reach, with no way to
point it at their own. The README documents environment-variable configuration —
wire `config.py` to match (resolve at runtime, not import time, with a friendly
error if unset):

```python
import os
from pathlib import Path

def _require(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise SystemExit(f"{var} is not set. Export it, e.g. {var}=https://your-org.atlassian.net")
    return val

JIRA_INSTANCE = _require("JSM_JIRA_INSTANCE")
PROJECT_KEY = _require("JSM_PROJECT_KEY")
OUTPUT_DIR = Path(os.environ.get("JSM_OUTPUT_DIR", Path.home() / "Analytics" / "JSM"))
```

(Keep secrets in the keychain as today — only the non-secret instance/project/output
move to env vars.)

### 2. `models.py:14` — real host in a docstring comment (ships in wheel)

```python
url: str   # https://servicedesk.inside-box.net/browse/IT-4821
```
→ change to `https://your-org.atlassian.net/browse/IT-1042`.

### 3. `tests/` — real domain + emails (2 files ship in the sdist)

`tests/test_writer.py` and `tests/test_all_time_appender.py` are included in the
sdist; the fixtures are not, but they're in the public repo. Replace the domain
across all four files:

- `tests/test_writer.py` — `inside-box.net` host + `test.user@inside-box.net`, `reporter@inside-box.net`
- `tests/test_all_time_appender.py` — `inside-box.net` host (8 occurrences)
- `tests/fixtures/sample_ticket.json` — host + `alex.rivera@inside-box.net`, `jordan.chen@inside-box.net`
- `tests/fixtures/sample_ticket_unresolved.json` — host + `morgan.lee@inside-box.net`

Recommended global substitution in `tests/`: `inside-box.net` → `example.com` (and
`servicedesk.inside-box.net` → `your-org.atlassian.net`). Re-run `uv run pytest`
after — these are string fixtures, so tests stay green.

### 4. `com.saagar.jsm-export.plist` — personal name + absolute home paths

Filename and contents leak your name, `/Users/d/...` paths, and your mise Python
path. It does **not** ship in the PyPI artifacts, but it's in the public repo.
Replace with the sanitized template at the bottom of this file (and rename to
`com.example.jsm-export.plist`). Note: renaming cascades to references in
`IMPLEMENTATION-ROADMAP.md` and `docs/PORTFOLIO-DISPOSITION.md`.

### 5. `AGENTS.md` (Codex-owned) + internal docs

- `AGENTS.md:9` — `servicedesk.inside-box.net`. Owned by Codex; flag for that lane.
- `docs/PORTFOLIO-DISPOSITION.md` and `DOC-RECONCILIATION.md` — internal portfolio
  artifacts (reference the plist name / your GitHub handle). They have no value to
  end users; recommend removing them from the public repo rather than shipping them.

### Verify the gate is clear

```bash
# Should print NOTHING once source/tests are sanitized:
grep -rniE "inside-box|servicedesk|/Users/|mise/installs" . \
  --include='*.py' --include='*.json' --include='*.plist' --include='*.md' --include='*.toml' \
  | grep -vE '\.bak|/\.venv/|/dist/|RELEASE\.md'
```

---

## Release steps

### 0. Prerequisites (one time)

- PyPI account + API token: https://pypi.org/manage/account/token/
- TestPyPI account + token (for the dry run): https://test.pypi.org/manage/account/token/

### 1. Bump the version & changelog

- `pyproject.toml` → `version` (currently `0.1.0`)
- `CHANGELOG.md` → move items from `[Unreleased]` into a dated `[0.1.0]` section

### 2. Verify the gate

```bash
uv sync --all-groups
uv run pytest
```

### 3. Build fresh artifacts

```bash
rm -rf dist
uv build           # → dist/*.tar.gz (sdist) + dist/*.whl (wheel)
uvx twine check dist/*
```

Confirm the wheel ships only what it should:

```bash
unzip -l dist/*.whl
```

### 4. Dry run on TestPyPI

```bash
uvx twine upload --repository testpypi dist/*
```

Then install it into a throwaway environment and smoke-test the entry point.
(TestPyPI doesn't host `requests`/`keyring`, so point deps at real PyPI.)

```bash
python -m venv /tmp/jsm-test
/tmp/jsm-test/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  jsm-ticket-analytics-export
/tmp/jsm-test/bin/jsm-export --help          # argparse help; confirms entry point resolves
which /tmp/jsm-test/bin/jsm-export-setup     # confirm the second script installed (it's interactive)
rm -rf /tmp/jsm-test
```

### 5. Publish to PyPI (real)

```bash
uvx twine upload dist/*
# Username: __token__
# Password: <your PyPI API token, including the "pypi-" prefix>
```

Or store the token in `~/.pypirc` / `UV_PUBLISH_TOKEN` and use `uv publish`.

### 6. Verify the live release

```bash
pip install jsm-ticket-analytics-export
jsm-export --help
```

Check the project page: https://pypi.org/project/jsm-ticket-analytics-export/

### 7. Tag the release (in git)

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

---

## Sanitized launchd template

Save as `com.example.jsm-export.plist`. Replace the two `__...__` placeholders with
absolute paths for your machine (launchd does not expand `~` or `$HOME`). The
recommended target is the installed console script rather than the source file.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.example.jsm-export</string>

    <key>ProgramArguments</key>
    <array>
        <string>__ABSOLUTE_PATH_TO__/jsm-export</string>
        <string>--month</string>
        <string>auto</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>JSM_JIRA_INSTANCE</key>
        <string>https://your-org.atlassian.net</string>
        <key>JSM_PROJECT_KEY</key>
        <string>SUPPORT</string>
    </dict>

    <!-- Run on the 1st of every month at 06:00 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key><integer>1</integer>
        <key>Hour</key><integer>6</integer>
        <key>Minute</key><integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>__ABSOLUTE_PATH_TO__/Analytics/JSM/logs/jsm-export-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>__ABSOLUTE_PATH_TO__/Analytics/JSM/logs/jsm-export-stderr.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Install:

```bash
cp com.example.jsm-export.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.jsm-export.plist
launchctl list | grep jsm        # confirm loaded
launchctl start com.example.jsm-export   # manual test trigger
```
