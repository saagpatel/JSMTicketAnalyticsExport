"""One-time interactive credential setup for JSM Ticket Analytics Export.

Prompts for a Jira email address and API token, stores them in macOS
Keychain via ``keyring``, then validates the credentials against the live
Jira API before exiting.

Usage::

    python setup_keychain.py

Re-running this script overwrites any previously stored credentials.
"""

import getpass
import logging
import sys

import keyring

import config
from jira_client import JiraAPIError, validate_auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def store_credentials(email: str, api_token: str) -> None:
    """Persist Jira credentials to macOS Keychain.

    Args:
        email: Atlassian account email address.
        api_token: Jira API token (not the account password).
    """
    keyring.set_password(config.KEYRING_SERVICE, config.KEYRING_EMAIL_KEY, email)
    logger.debug("Stored email under %s/%s", config.KEYRING_SERVICE, config.KEYRING_EMAIL_KEY)

    keyring.set_password(config.KEYRING_SERVICE, config.KEYRING_TOKEN_KEY, api_token)
    logger.debug("Stored token under %s/%s", config.KEYRING_SERVICE, config.KEYRING_TOKEN_KEY)


def prompt_credentials() -> tuple[str, str]:
    """Interactively collect Jira credentials from the operator.

    The API token is read via ``getpass`` so it is never echoed to the
    terminal.

    Returns:
        (email, api_token) tuple with leading/trailing whitespace stripped.
    """
    print(f"\nJSM Analytics — Credential Setup")
    print(f"Instance: {config.JIRA_INSTANCE}\n")

    email = input("Atlassian account email: ").strip()
    if not email:
        raise ValueError("Email must not be empty.")

    api_token = getpass.getpass("Jira API token (input hidden): ").strip()
    if not api_token:
        raise ValueError("API token must not be empty.")

    return email, api_token


def main() -> None:
    """Run the interactive credential setup flow."""
    try:
        email, api_token = prompt_credentials()
    except ValueError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)

    print("\nStoring credentials in macOS Keychain...", end=" ", flush=True)
    try:
        store_credentials(email, api_token)
    except Exception as exc:
        print("FAILED", file=sys.stderr)
        logger.error("Failed to write to keychain: %s", exc)
        sys.exit(1)
    print("done.")

    print("Validating credentials against Jira API...", end=" ", flush=True)
    try:
        display_name = validate_auth()
    except JiraAPIError as exc:
        print("FAILED", file=sys.stderr)
        print(
            f"\nAuth validation failed (HTTP {exc.status_code}). "
            "Check that your email and API token are correct.\n"
            f"API response: {exc.response_body[:200]}",
            file=sys.stderr,
        )
        sys.exit(1)
    except RuntimeError as exc:
        # Should not happen since we just stored creds, but handle defensively.
        print("FAILED", file=sys.stderr)
        print(f"\nCredential lookup error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print("FAILED", file=sys.stderr)
        logger.error("Unexpected error during auth validation: %s", exc, exc_info=True)
        sys.exit(1)

    print(f"\n✓ Auth validated: {display_name}")


if __name__ == "__main__":
    main()
