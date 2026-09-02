"""Deterministic tests for the best-effort SMTP notification channel."""

from __future__ import annotations

import asyncio
import smtplib
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

import bot
from smtp_notifier import (
    SmtpConfig,
    SmtpConfigurationError,
    SmtpNotifier,
    build_smtp_notifier,
)

TEST_PASSWORD = "test-password-not-a-real-secret"


def _runtime_config(**overrides: object) -> SimpleNamespace:
    values = {
        "SMTP_HOST": "smtp.example.invalid",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "grant-bot@example.invalid",
        "SMTP_PASSWORD": TEST_PASSWORD,
        "SMTP_FROM": "grant-bot@example.invalid",
        "SMTP_TO": "ops@example.invalid, grants@example.invalid",
        "SMTP_SECURITY": "STARTTLS",
        "SMTP_TIMEOUT": "7.5",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _grant() -> dict[str, object]:
    return {
        "title": "Community Robotics Grant",
        "end_date": date(2026, 10, 31),
        "url": "https://example.invalid/apply",
        "description": "Travel and registration support.",
    }


def test_valid_smtp_config() -> None:
    smtp_config = SmtpConfig.from_runtime_config(_runtime_config())

    assert smtp_config is not None
    assert smtp_config.host == "smtp.example.invalid"
    assert smtp_config.port == 587
    assert smtp_config.recipients == (
        "ops@example.invalid",
        "grants@example.invalid",
    )
    assert smtp_config.security == "STARTTLS"
    assert smtp_config.timeout == 7.5


def test_missing_mandatory_smtp_config() -> None:
    runtime_config = _runtime_config(SMTP_PASSWORD=None, SMTP_TO=None)

    with pytest.raises(SmtpConfigurationError) as error:
        SmtpConfig.from_runtime_config(runtime_config)

    assert "SMTP_PASSWORD" in str(error.value)
    assert "SMTP_TO" in str(error.value)
    assert TEST_PASSWORD not in str(error.value)


def test_partial_config_disables_channel_without_logging_secret(
    caplog: pytest.LogCaptureFixture,
) -> None:
    notifier = build_smtp_notifier(_runtime_config(SMTP_TO=None))

    assert notifier is None
    assert "SMTP_TO" in caplog.text
    assert TEST_PASSWORD not in caplog.text


def test_successful_mail_delivery_uses_starttls() -> None:
    smtp_config = SmtpConfig.from_runtime_config(_runtime_config())
    assert smtp_config is not None
    notifier = SmtpNotifier(smtp_config)
    tls_context = Mock()

    with (
        patch("smtp_notifier.ssl.create_default_context", return_value=tls_context),
        patch("smtp_notifier.smtplib.SMTP") as smtp_class,
    ):
        smtp = smtp_class.return_value.__enter__.return_value

        delivered = notifier.send_grant(_grant())

    assert delivered is True
    smtp_class.assert_called_once_with(
        "smtp.example.invalid",
        587,
        timeout=7.5,
    )
    assert smtp.ehlo.call_count == 2
    smtp.starttls.assert_called_once_with(context=tls_context)
    smtp.login.assert_called_once_with(
        "grant-bot@example.invalid",
        TEST_PASSWORD,
    )
    message = smtp.send_message.call_args.args[0]
    assert message["Subject"] == "New grant: Community Robotics Grant"
    assert "Deadline: 2026-10-31" in message.get_content()
    assert "URL: https://example.invalid/apply" in message.get_content()
    assert "Description: Travel and registration support." in message.get_content()


def test_successful_mail_delivery_supports_implicit_ssl() -> None:
    smtp_config = SmtpConfig.from_runtime_config(
        _runtime_config(SMTP_PORT="465", SMTP_SECURITY="SSL")
    )
    assert smtp_config is not None
    notifier = SmtpNotifier(smtp_config)
    tls_context = Mock()

    with (
        patch("smtp_notifier.ssl.create_default_context", return_value=tls_context),
        patch("smtp_notifier.smtplib.SMTP_SSL") as smtp_ssl_class,
        patch("smtp_notifier.smtplib.SMTP") as smtp_class,
    ):
        smtp = smtp_ssl_class.return_value.__enter__.return_value

        delivered = notifier.send_grant(_grant())

    assert delivered is True
    smtp_ssl_class.assert_called_once_with(
        "smtp.example.invalid",
        465,
        timeout=7.5,
        context=tls_context,
    )
    smtp.login.assert_called_once()
    smtp.send_message.assert_called_once()
    smtp_class.assert_not_called()


def test_smtp_timeout_is_contained(caplog: pytest.LogCaptureFixture) -> None:
    smtp_config = SmtpConfig.from_runtime_config(_runtime_config())
    assert smtp_config is not None
    notifier = SmtpNotifier(smtp_config)

    with patch("smtp_notifier.smtplib.SMTP", side_effect=TimeoutError):
        delivered = notifier.send_grant(_grant())

    assert delivered is False
    assert "TimeoutError" in caplog.text
    assert TEST_PASSWORD not in caplog.text


def test_authentication_failure_is_contained_and_redacted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    smtp_config = SmtpConfig.from_runtime_config(_runtime_config())
    assert smtp_config is not None
    notifier = SmtpNotifier(smtp_config)

    with patch("smtp_notifier.smtplib.SMTP") as smtp_class:
        smtp = smtp_class.return_value.__enter__.return_value
        smtp.login.side_effect = smtplib.SMTPAuthenticationError(
            535,
            f"Authentication rejected: {TEST_PASSWORD}".encode(),
        )

        delivered = notifier.send_grant(_grant())

    assert delivered is False
    assert "SMTPAuthenticationError" in caplog.text
    assert TEST_PASSWORD not in caplog.text
    smtp.send_message.assert_not_called()


def test_smtp_failure_does_not_interrupt_telegram_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    grant = {
        "title": "Community Robotics Grant",
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 10, 31),
        "url": "https://example.invalid/apply",
    }
    notification = {
        "notification_id": 11,
        "grant_id": 22,
        "chat_id": 12345,
        "grant_title": grant["title"],
        "start_date": grant["start_date"],
        "end_date": grant["end_date"],
        "grant_url": grant["url"],
    }
    application = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

    class FailingNotifier:
        def send_grant(self, sent_grant: dict[str, object]) -> bool:
            assert sent_grant == grant
            assert application.bot.send_message.await_count == 1
            raise TimeoutError(TEST_PASSWORD)

    async def cancel_after_cycle(_delay: int) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(bot, "last_scrape_time", 0)
    monkeypatch.setattr(bot.config, "CHECK_INTERVAL", 0)
    monkeypatch.setattr(bot, "smtp_notifier", FailingNotifier())
    monkeypatch.setattr(bot.Scraper, "scrape", lambda: [grant])
    monkeypatch.setattr(bot.DB, "increment_scrapes", lambda: None)
    monkeypatch.setattr(bot.DB, "get_all_grants", lambda: [])
    monkeypatch.setattr(bot.DB, "get_subscribed_users", lambda: [12345])
    monkeypatch.setattr(bot.DB, "add_grant", lambda **_grant: 22)
    monkeypatch.setattr(
        bot.DB,
        "create_pending_notification",
        lambda _chat_id, _grant_id: True,
    )
    monkeypatch.setattr(
        bot.DB,
        "get_pending_notifications",
        lambda: [notification],
    )
    monkeypatch.setattr(bot.DB, "mark_notification_sent", lambda _id: True)
    monkeypatch.setattr(bot.DB, "increment_notifications", lambda: None)
    monkeypatch.setattr(bot.DB, "update_user_count", lambda: None)
    monkeypatch.setattr(bot.asyncio, "sleep", cancel_after_cycle)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bot.scrape_and_notify_loop(application))

    application.bot.send_message.assert_awaited_once_with(
        chat_id=12345,
        text=(
            "🚨 *FIRST SİTESİNDE YENİ HİBE BİLDİRİMİ!* 🚨\n\n"
            "1. *Community Robotics Grant*\n"
            "   🔗 [Başvuru Linki](https://example.invalid/apply)\n"
            "   📅 01.09.2026 → 31.10.2026\n\n"
        ),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    assert TEST_PASSWORD not in capsys.readouterr().out
