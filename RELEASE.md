# Release Guide — Publishing to PyPI

Operator runbook for cutting a release of `jsm-ticket-analytics-export` to PyPI.
Assumes a PyPI account and an API token.

---

## Sanitization status: ✅ clean

The package is free of organisation-specific values:

- `config.py` reads `JSM_JIRA_INSTANCE` / `JSM_PROJECT_KEY` / `JSM_OUTPUT_DIR` from
  the environment — nothing instance-specific is baked into the published code.
- Sample data in tests and fixtures uses synthetic placeholders
  (`https://your-org.atlassian.net`, `@example.com`).
- The launchd template ships as `com.example.jsm-export.plist` with placeholder paths.

### Pre-flight verification (should print nothing)

```bash
# No personal absolute paths or runtime paths in tracked files:
git grep -nE "/Users/|mise/installs" -- . ':(exclude)*.bak'

# And confirm your real Jira hostname appears nowhere (substitute it):
# git grep -ni "your-real-hostname" -- . ':(exclude)*.bak'
```

The shipped artifacts are verified clean — scanning the built wheel and sdist
for any internal hostname returns zero matches.

> Note: `AGENTS.md` is owned by Codex and is sanitized for public repo visibility.

---

## Release steps

### 0. Prerequisites (one time)

- PyPI API token: https://pypi.org/manage/account/token/
- TestPyPI account + token (for the dry run): https://test.pypi.org/manage/account/token/

### 1. Bump version & changelog

- `pyproject.toml` → `version` (currently `0.1.0`)
- `CHANGELOG.md` → move items from `[Unreleased]` into a dated release section

### 2. Verify the gate

```bash
uv sync --all-groups
uv run pytest
```

### 3. Build fresh artifacts

```bash
rm -rf dist
uv build                 # → dist/*.tar.gz (sdist) + dist/*.whl (wheel)
uvx twine check dist/*
unzip -l dist/*.whl      # confirm only the modules + LICENSE + metadata ship
```

### 4. Dry run on TestPyPI

```bash
uvx twine upload --repository testpypi dist/*
```

Install into a throwaway environment and smoke-test the entry points.
(TestPyPI doesn't host `requests`/`keyring`, so point deps at real PyPI.)

```bash
python -m venv /tmp/jsm-test
/tmp/jsm-test/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  jsm-ticket-analytics-export
/tmp/jsm-test/bin/jsm-export --help          # argparse help; confirms entry point resolves
which /tmp/jsm-test/bin/jsm-export-setup      # confirm the second script installed (it's interactive)
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
export JSM_JIRA_INSTANCE="https://your-org.atlassian.net"
export JSM_PROJECT_KEY="SUPPORT"
jsm-export --help
```

Project page: https://pypi.org/project/jsm-ticket-analytics-export/

### 7. Tag the release (in git)

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

---

## Scheduling with launchd (optional)

`com.example.jsm-export.plist` is a ready template. Replace every
`__ABSOLUTE_PATH_TO__` placeholder with an absolute path for your machine
(launchd does not expand `~` or `$HOME`) and set the env vars in the
`EnvironmentVariables` block. Then:

```bash
cp com.example.jsm-export.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.jsm-export.plist
launchctl list | grep jsm                 # confirm loaded
launchctl start com.example.jsm-export     # manual test trigger
```
