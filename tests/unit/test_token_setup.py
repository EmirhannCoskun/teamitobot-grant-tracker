"""Tests for the non-persisting Telegram token setup CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from tools.token_setup.validator import (
    ValidationStatus,
    validate_token,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VALID_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_123456789"
INVALID_TOKEN = "123456789:INVALIDTOKEN123456789"
SECRET_SENTINEL = "987654321:SUPER_SECRET_TOKEN_DO_NOT_EXPOSE"


def _subprocess_environment() -> dict[str, str]:
    """Build an environment that can import the project from any cwd."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def test_validate_token_returns_valid_for_successful_get_me(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"ok": True, "result": {"is_bot": True}}

    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)

    result = validate_token(VALID_TOKEN)

    assert result.status is ValidationStatus.VALID
    get.assert_called_once()


def test_validate_token_returns_invalid_for_http_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Mock()
    response.status_code = 401

    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)

    result = validate_token(INVALID_TOKEN)

    assert result.status is ValidationStatus.INVALID


def test_validate_token_returns_unavailable_for_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get = Mock(side_effect=requests.RequestException("network failure"))
    monkeypatch.setattr(requests, "get", get)

    result = validate_token(VALID_TOKEN)

    assert result.status is ValidationStatus.UNAVAILABLE


def test_validate_token_returns_unavailable_for_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Mock()
    response.status_code = 500

    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)

    result = validate_token(VALID_TOKEN)

    assert result.status is ValidationStatus.UNAVAILABLE


def test_validate_token_does_not_store_token_in_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"ok": True}

    monkeypatch.setattr(requests, "get", Mock(return_value=response))

    result = validate_token(SECRET_SENTINEL)

    assert result.status is ValidationStatus.VALID
    assert SECRET_SENTINEL not in repr(result)
    assert SECRET_SENTINEL not in str(result)


def test_validate_token_does_not_include_token_in_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_get(*args: object, **kwargs: object) -> None:
        raise requests.RequestException("request failed")

    monkeypatch.setattr(requests, "get", failing_get)

    result = validate_token(SECRET_SENTINEL)

    assert result.status is ValidationStatus.UNAVAILABLE


def test_cli_reports_missing_environment_variable_without_token(
    tmp_path: Path,
) -> None:
    environment = _subprocess_environment()
    environment.pop("TELEGRAM_BOT_TOKEN", None)

    result = subprocess.run(
        [sys.executable, "-m", "tools.token_setup"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "TELEGRAM_BOT_TOKEN is not set in the environment." in result.stderr
    assert result.stdout == ""
    assert not list(tmp_path.iterdir())


def test_cli_does_not_echo_token_from_environment(
    tmp_path: Path,
) -> None:
    environment = _subprocess_environment()
    environment["TELEGRAM_BOT_TOKEN"] = SECRET_SENTINEL

    result = subprocess.run(
        [sys.executable, "-m", "tools.token_setup"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    combined_output = result.stdout + result.stderr

    assert SECRET_SENTINEL not in combined_output
    assert result.returncode in {0, 1, 2}
    assert not list(tmp_path.iterdir())


def test_cli_does_not_create_token_file(tmp_path: Path) -> None:
    environment = _subprocess_environment()
    environment["TELEGRAM_BOT_TOKEN"] = "not-a-valid-token"

    result = subprocess.run(
        [sys.executable, "-m", "tools.token_setup"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert (
        "TELEGRAM_BOT_TOKEN does not have a valid Telegram bot token format."
        in result.stderr
    )
    assert not list(tmp_path.iterdir())
