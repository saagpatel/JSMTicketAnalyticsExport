"""Non-secret configuration constants for JSM Ticket Analytics Export.

Instance, project key, and output directory are read from environment
variables so the tool is portable across Jira instances and no
organisation-specific values are baked into the published package.
Credentials are never read here — they live in the OS keychain
(see setup_keychain.py).
"""

import os
from pathlib import Path

# Required at runtime; validated in jsm_export.main() with a friendly error.
JIRA_INSTANCE = os.environ.get("JSM_JIRA_INSTANCE", "")
PROJECT_KEY = os.environ.get("JSM_PROJECT_KEY", "")

OUTPUT_DIR = Path(
    os.environ.get("JSM_OUTPUT_DIR", str(Path.home() / "Analytics" / "JSM"))
)
LOG_DIR = OUTPUT_DIR / "logs"

KEYRING_SERVICE = "jsm-analytics"
KEYRING_TOKEN_KEY = "api-token"
KEYRING_EMAIL_KEY = "email"

MAX_RESULTS_PER_PAGE = 100
RATE_LIMIT_RPS = 8.0
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2.0

DEFAULT_JQL_ORDER = "ORDER BY created ASC"
