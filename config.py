"""Local bootstrap and compatibility access for application settings.

Canonical precedence is process environment > local ``.env`` > documented
defaults. ``.env`` is considered only for local development bootstrap; test,
staging, and production use their explicit environment/secret store.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from infrastructure.config import Settings, settings_from_mapping

_LOCAL_ENVIRONMENTS = frozenset({"development"})


def load_settings(
    environ: Mapping[str, str] | None = None,
    *,
    dotenv_path: str | os.PathLike[str] | None = None,
    use_dotenv: bool = True,
) -> Settings:
    """Load settings once using the canonical source precedence.

    Supplying ``environ`` makes tests deterministic without mutating
    ``os.environ``. Explicit environment values always win over ``.env``.
    """
    environment_values = dict(os.environ if environ is None else environ)
    mode = environment_values.get("ENVIRONMENT", "development").strip().casefold()
    merged_values: dict[str, str] = {}

    if use_dotenv and mode in _LOCAL_ENVIRONMENTS:
        path = Path(dotenv_path) if dotenv_path is not None else Path.cwd() / ".env"
        if path.is_file():
            merged_values.update(
                {
                    key: value
                    for key, value in dotenv_values(
                        path,
                        interpolate=False,
                    ).items()
                    if value is not None
                }
            )
    merged_values.update(environment_values)
    return settings_from_mapping(merged_values)


class Config:
    """Temporary uppercase compatibility facade over immutable ``Settings``."""

    _COMPATIBILITY_ATTRIBUTES = {
        "BOT_TOKEN": lambda settings: settings.telegram_bot_token,
        "DATABASE_URL": lambda settings: settings.database_url,
        "ENVIRONMENT": lambda settings: settings.environment.value,
        "RELEASE_ID": lambda settings: settings.release_id,
        "CHECK_INTERVAL": lambda settings: settings.check_interval_seconds,
        "LOG_LEVEL": lambda settings: settings.log_level.value,
        "PORT": lambda settings: settings.health_port,
        "GRANT_URL": lambda settings: settings.grant_url,
        "REQUEST_TIMEOUT": lambda settings: settings.provider_timeout_seconds,
        "PROVIDER_TIMEOUT": lambda settings: settings.provider_timeout_seconds,
        "TELEGRAM_TIMEOUT": lambda settings: settings.telegram_timeout_seconds,
        "DATABASE_TIMEOUT": lambda settings: settings.database_timeout_seconds,
        "POLLING_BACKLOG_POLICY": (
            lambda settings: settings.polling_backlog_policy.value
        ),
        "OUTBOX_MAX_ATTEMPTS": lambda settings: settings.outbox_max_attempts,
        "OUTBOX_BASE_BACKOFF": (lambda settings: settings.outbox_base_backoff_seconds),
        "OUTBOX_MAX_BACKOFF": (lambda settings: settings.outbox_max_backoff_seconds),
        "OUTBOX_LEASE_SECONDS": lambda settings: settings.outbox_lease_seconds,
        "SMTP_HOST": lambda settings: settings.smtp.host,
        "SMTP_PORT": lambda settings: settings.smtp.port,
        "SMTP_USERNAME": lambda settings: settings.smtp.username,
        "SMTP_PASSWORD": lambda settings: settings.smtp.password,
        "SMTP_FROM": lambda settings: settings.smtp.sender,
        "SMTP_TO": lambda settings: settings.smtp.recipients,
        "SMTP_SECURITY": lambda settings: settings.smtp.security,
        "SMTP_TIMEOUT": lambda settings: settings.smtp.timeout,
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def __getattr__(self, name: str) -> Any:
        accessor = self._COMPATIBILITY_ATTRIBUTES.get(name)
        if accessor is None:
            raise AttributeError(name)
        return accessor(self.settings)

    def __repr__(self) -> str:
        return f"Config({dict(self.settings.redacted_summary())!r})"

    def validate(self) -> bool:
        """Retain the legacy validation entrypoint; construction already validates."""
        return True


settings = load_settings()
config = Config(settings)
