"""Jira REST API v3 client for JSM Ticket Analytics Export.

Provides authenticated, rate-limited, retry-wrapped HTTP access to the
Jira REST API. All credentials are read from macOS Keychain via keyring —
never from env vars or config files.
"""

import logging
import random
import time
from collections.abc import Generator
from typing import Any

import keyring
import requests

import config

logger = logging.getLogger(__name__)


class JiraAPIError(Exception):
    """Raised for non-retryable HTTP errors from the Jira API."""

    def __init__(self, message: str, status_code: int, response_body: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class _TokenBucket:
    """Simple fixed-interval rate limiter.

    Enforces a minimum interval between acquisitions so that callers
    do not exceed ``rate`` requests per second on average. Sleeps the
    calling thread as needed.
    """

    def __init__(self, rate: float = 8.0) -> None:
        """Initialise the bucket.

        Args:
            rate: Maximum allowed requests per second.
        """
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        self._interval: float = 1.0 / rate
        self._last_call: float = 0.0

    def acquire(self) -> None:
        """Block until the next request slot is available."""
        now = time.monotonic()
        elapsed = now - self._last_call
        wait = self._interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()


# Module-level singleton — shared across all api_get() calls.
_rate_limiter = _TokenBucket(rate=config.RATE_LIMIT_RPS)


def _get_auth() -> tuple[str, str]:
    """Retrieve Jira credentials from macOS Keychain.

    Returns:
        (email, api_token) tuple ready for HTTP Basic auth.

    Raises:
        RuntimeError: If either credential is absent from the keychain.
    """
    email: str | None = keyring.get_password(
        config.KEYRING_SERVICE, config.KEYRING_EMAIL_KEY
    )
    token: str | None = keyring.get_password(
        config.KEYRING_SERVICE, config.KEYRING_TOKEN_KEY
    )

    missing: list[str] = []
    if not email:
        missing.append(f"{config.KEYRING_SERVICE}/{config.KEYRING_EMAIL_KEY}")
    if not token:
        missing.append(f"{config.KEYRING_SERVICE}/{config.KEYRING_TOKEN_KEY}")

    if missing:
        raise RuntimeError(
            "Missing Jira credentials in keychain. "
            f"Run setup_keychain.py to store them. Missing: {', '.join(missing)}"
        )

    return email, token  # type: ignore[return-value]  # narrowed above


def api_get(
    path: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Perform an authenticated GET request against the Jira REST API.

    Automatically:
    - Rate-limits via the module-level token bucket.
    - Retries on 429 (Too Many Requests) and 5xx responses with
      exponential back-off plus ±25 % random jitter.
    - Raises immediately on non-retryable 4xx errors.

    Args:
        path: API path relative to the Jira instance root
              (e.g. ``"/rest/api/3/myself"``).
        params: Optional query-string parameters.

    Returns:
        Parsed JSON response body as a dict.

    Raises:
        JiraAPIError: For non-retryable HTTP error responses.
        RuntimeError: If credentials are absent from the keychain.
        requests.exceptions.RequestException: For unrecoverable network
            failures after all retries are exhausted.
    """
    url = f"{config.JIRA_INSTANCE}{path}"
    auth = _get_auth()
    headers = {"Accept": "application/json"}

    last_exc: Exception | None = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        _rate_limiter.acquire()

        try:
            response = requests.get(
                url,
                auth=auth,
                headers=headers,
                params=params,
                timeout=(5, 30),
            )
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Network error on attempt %d/%d for %s: %s",
                attempt,
                config.MAX_RETRIES,
                path,
                exc,
            )
            if attempt < config.MAX_RETRIES:
                _sleep_backoff(attempt)
            continue

        status = response.status_code

        # Success path
        if 200 <= status < 300:
            return response.json()

        # Retryable: 429 and any 5xx
        if status == 429 or status >= 500:
            logger.warning(
                "Retryable HTTP %d on attempt %d/%d for %s",
                status,
                attempt,
                config.MAX_RETRIES,
                path,
            )
            last_exc = JiraAPIError(
                f"HTTP {status}",
                status_code=status,
                response_body=response.text,
            )
            if attempt < config.MAX_RETRIES:
                _sleep_backoff(attempt)
            continue

        # Non-retryable 4xx
        raise JiraAPIError(
            f"Jira API returned HTTP {status} for {path}",
            status_code=status,
            response_body=response.text,
        )

    # All retries exhausted
    if isinstance(last_exc, JiraAPIError):
        raise last_exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"api_get exhausted {config.MAX_RETRIES} retries for {path}")


def _sleep_backoff(attempt: int) -> None:
    """Sleep for an exponentially growing, jittered duration.

    Args:
        attempt: The 1-based attempt number that just failed.
                 Used to compute the base delay (2^(attempt-1) × initial).
    """
    base = config.INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
    jitter = base * random.uniform(-0.25, 0.25)
    delay = max(0.0, base + jitter)
    logger.debug("Back-off: sleeping %.2fs before attempt %d", delay, attempt + 1)
    time.sleep(delay)


def validate_auth() -> str:
    """Confirm that stored credentials are accepted by the Jira API.

    Returns:
        The authenticated user's ``displayName`` string.

    Raises:
        JiraAPIError: If the API rejects the credentials.
        RuntimeError: If credentials are absent from the keychain.
    """
    data = api_get("/rest/api/3/myself")
    display_name: str = data["displayName"]
    logger.info("Authenticated as: %s", display_name)
    return display_name


def get_all_issues(
    jql: str,
    fields: list[str],
) -> Generator[dict[str, Any], None, None]:
    """Yield every Jira issue matching a JQL query, handling pagination.

    Uses ``startAt``-based cursor pagination as required by Jira REST API v3.
    Pagination terminates when the API returns an empty ``issues`` array,
    which is safer than comparing ``startAt`` to ``total`` (total can shift
    as tickets are created or deleted during a long export run).

    Args:
        jql: JQL query string (e.g. ``"project = IT ORDER BY created ASC"``).
        fields: List of field names/IDs to request from the API.

    Yields:
        Raw issue dicts as returned by the Jira API.

    Raises:
        JiraAPIError: On non-retryable API errors.
        RuntimeError: If credentials are absent.
    """
    start_at = 0
    total: int | None = None
    fetched = 0

    while True:
        params: dict[str, str] = {
            "jql": jql,
            "startAt": str(start_at),
            "maxResults": str(config.MAX_RESULTS_PER_PAGE),
            "fields": ",".join(fields),
        }

        data = api_get("/rest/api/3/search", params=params)

        # Capture total on the first page for progress logging only.
        if total is None:
            total = int(data.get("total", 0))
            logger.info("Total tickets to fetch: %d", total)

        issues: list[dict[str, Any]] = data.get("issues", [])

        if not issues:
            break

        for issue in issues:
            yield issue

        fetched += len(issues)
        start_at += len(issues)

        logger.info("Fetched %d/%d tickets...", fetched, total)

    # Warn if the count drifted more than 0.1 % from the initial total.
    if total is not None and total > 0:
        drift = abs(fetched - total) / total
        if drift > 0.001:
            logger.warning(
                "Ticket count mismatch: expected %d (initial total) but fetched %d "
                "(%.2f%% drift — tickets may have been created/deleted during export).",
                total,
                fetched,
                drift * 100,
            )

    logger.info("Export complete. Total tickets fetched: %d", fetched)
