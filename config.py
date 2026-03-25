"""Non-secret configuration constants for JSM Ticket Analytics Export."""

from pathlib import Path

JIRA_INSTANCE = "https://servicedesk.inside-box.net"
PROJECT_KEY = "IT"
OUTPUT_DIR = Path.home() / "Analytics" / "JSM"
LOG_DIR = OUTPUT_DIR / "logs"

KEYRING_SERVICE = "jsm-analytics"
KEYRING_TOKEN_KEY = "api-token"
KEYRING_EMAIL_KEY = "email"

MAX_RESULTS_PER_PAGE = 100
RATE_LIMIT_RPS = 8.0
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2.0

DEFAULT_JQL_ORDER = "ORDER BY created ASC"
