"""Best-effort SMTP notifications for newly discovered grants."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import getaddresses
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_SETTINGS = {
    "host": "SMTP_HOST",
    "port": "SMTP_PORT",
    "username": "SMTP_USERNAME",
    "password": "SMTP_PASSWORD",
    "sender": "SMTP_FROM",
    "recipients": "SMTP_TO",
}


class SmtpConfigurationError(ValueError):
    """Raised when the optional SMTP channel is only partly configured."""


@dataclass(frozen=True)
class SmtpConfig:
    """Validated SMTP settings sourced from the runtime configuration."""

    host: str
    port: int
    username: str
    password: str
    sender: str
    recipients: tuple[str, ...]
    security: str
    timeout: float

    @classmethod
    def from_runtime_config(cls, runtime_config: Any) -> SmtpConfig | None:
        """Build settings, returning ``None`` when SMTP is not configured."""
        raw = {
            name: getattr(runtime_config, environment_name, None)
            for name, environment_name in _REQUIRED_SETTINGS.items()
        }

        if not any(value for value in raw.values()):
            return None

        missing = [
            environment_name
            for name, environment_name in _REQUIRED_SETTINGS.items()
            if not raw[name]
        ]
        if missing:
            raise SmtpConfigurationError(
                "Missing required SMTP environment variables: " + ", ".join(missing)
            )

        port = _parse_port(str(raw["port"]))
        timeout = _parse_timeout(str(getattr(runtime_config, "SMTP_TIMEOUT", "10")))
        security = str(getattr(runtime_config, "SMTP_SECURITY", "STARTTLS")).upper()
        if security not in {"STARTTLS", "SSL"}:
            raise SmtpConfigurationError("SMTP_SECURITY must be STARTTLS or SSL")

        sender = str(raw["sender"])
        recipients = _parse_addresses(str(raw["recipients"]), "SMTP_TO")
        _parse_addresses(sender, "SMTP_FROM", expected_count=1)

        return cls(
            host=str(raw["host"]),
            port=port,
            username=str(raw["username"]),
            password=str(raw["password"]),
            sender=sender,
            recipients=recipients,
            security=security,
            timeout=timeout,
        )


class SmtpNotifier:
    """Send grant mail without allowing SMTP errors to escape."""

    def __init__(self, smtp_config: SmtpConfig) -> None:
        self.config = smtp_config

    def send_grant(self, grant: dict[str, Any]) -> bool:
        """Send one grant email and report whether the provider accepted it."""
        try:
            message = self._build_message(grant)
            tls_context = ssl.create_default_context()

            if self.config.security == "SSL":
                with smtplib.SMTP_SSL(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout,
                    context=tls_context,
                ) as smtp:
                    self._authenticate_and_send(smtp, message)
            else:
                with smtplib.SMTP(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout,
                ) as smtp:
                    smtp.ehlo()
                    smtp.starttls(context=tls_context)
                    smtp.ehlo()
                    self._authenticate_and_send(smtp, message)
        except Exception as error:  # SMTP is deliberately best-effort.
            logger.error(
                "SMTP grant notification failed (%s)",
                type(error).__name__,
            )
            return False

        return True

    def _authenticate_and_send(
        self,
        smtp: smtplib.SMTP,
        message: EmailMessage,
    ) -> None:
        smtp.login(self.config.username, self.config.password)
        smtp.send_message(message)

    def _build_message(self, grant: dict[str, Any]) -> EmailMessage:
        title = str(grant.get("title") or "Untitled grant")
        safe_subject_title = " ".join(title.split())[:120]

        lines = [f"Grant title: {title}"]
        deadline = grant.get("end_date")
        if deadline:
            lines.append(f"Deadline: {_format_date(deadline)}")

        url = grant.get("url")
        if url:
            lines.append(f"URL: {url}")

        description = grant.get("description")
        if description:
            lines.append(f"Description: {description}")

        message = EmailMessage()
        message["Subject"] = f"New grant: {safe_subject_title}"
        message["From"] = self.config.sender
        message["To"] = ", ".join(self.config.recipients)
        message.set_content("\n".join(lines))
        return message


def build_smtp_notifier(runtime_config: Any) -> SmtpNotifier | None:
    """Create the optional notifier without making startup SMTP-dependent."""
    try:
        smtp_config = SmtpConfig.from_runtime_config(runtime_config)
    except SmtpConfigurationError as error:
        logger.error("SMTP notifications disabled: %s", error)
        return None

    if smtp_config is None:
        return None

    return SmtpNotifier(smtp_config)


def _parse_port(raw_port: str) -> int:
    try:
        port = int(raw_port)
    except ValueError as error:
        raise SmtpConfigurationError("SMTP_PORT must be an integer") from error

    if not 1 <= port <= 65535:
        raise SmtpConfigurationError("SMTP_PORT must be between 1 and 65535")
    return port


def _parse_timeout(raw_timeout: str) -> float:
    try:
        timeout = float(raw_timeout)
    except ValueError as error:
        raise SmtpConfigurationError("SMTP_TIMEOUT must be a number") from error

    if timeout <= 0:
        raise SmtpConfigurationError("SMTP_TIMEOUT must be positive")
    return timeout


def _parse_addresses(
    raw_addresses: str,
    setting_name: str,
    expected_count: int | None = None,
) -> tuple[str, ...]:
    if "\r" in raw_addresses or "\n" in raw_addresses:
        raise SmtpConfigurationError(f"{setting_name} must contain valid email")

    parsed = tuple(
        address
        for _, address in getaddresses([raw_addresses])
        if address and "@" in address
    )
    if not parsed or (expected_count is not None and len(parsed) != expected_count):
        raise SmtpConfigurationError(f"{setting_name} must contain valid email")
    return parsed


def _format_date(value: Any) -> str:
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)
