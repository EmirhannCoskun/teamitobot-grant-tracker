"""Command-line interface for non-persisting Telegram token validation."""

from __future__ import annotations

import os
import re
import sys
from typing import Final

from .validator import (
    TELEGRAM_BOT_TOKEN_ENV,
    ValidationStatus,
    validate_token,
)

EXIT_VALID: Final = 0
EXIT_INVALID: Final = 1
EXIT_UNAVAILABLE: Final = 2

# Telegram bot tokens currently use the form:
# <bot-id>:<secret>
# The exact secret length is intentionally not enforced because Telegram
# controls the token format and may change it independently of this tool.
TOKEN_PATTERN: Final = re.compile(r"^\d+:[A-Za-z0-9_-]+$")

MESSAGE_VALID: Final = "Telegram bot token is valid."
MESSAGE_INVALID: Final = "Telegram bot token is invalid."
MESSAGE_UNAVAILABLE: Final = (
    "Telegram Bot API could not be reached or returned an unexpected response."
)
MESSAGE_MISSING: Final = f"{TELEGRAM_BOT_TOKEN_ENV} is not set in the environment."
MESSAGE_FORMAT: Final = (
    f"{TELEGRAM_BOT_TOKEN_ENV} does not have a valid Telegram bot token format."
)


def _read_token() -> str | None:
    """Read the token from the canonical process environment."""
    token = os.environ.get(TELEGRAM_BOT_TOKEN_ENV)

    if token is None:
        return None

    return token.strip()


def _has_valid_format(token: str) -> bool:
    """Check the locally recognizable structure of a Telegram bot token."""
    return bool(TOKEN_PATTERN.fullmatch(token))


def main() -> int:
    """Run token validation and return a process exit code."""
    token = _read_token()

    if token is None or not token:
        print(MESSAGE_MISSING, file=sys.stderr)
        return EXIT_INVALID

    if not _has_valid_format(token):
        print(MESSAGE_FORMAT, file=sys.stderr)
        return EXIT_INVALID

    result = validate_token(token)

    if result.status is ValidationStatus.VALID:
        print(MESSAGE_VALID)
        return EXIT_VALID

    if result.status is ValidationStatus.INVALID:
        print(MESSAGE_INVALID, file=sys.stderr)
        return EXIT_INVALID

    print(MESSAGE_UNAVAILABLE, file=sys.stderr)
    return EXIT_UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
