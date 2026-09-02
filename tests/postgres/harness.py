"""
İzole PostgreSQL test altyapısı için yardımcı fonksiyonlar
"""

from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.engine import Engine

SAFE_TEST_HOSTS = {"localhost", "127.0.0.1"}


def guard_test_database_url(url: str) -> None:
    """TEST_DATABASE_URL production'a benzer bir hedefe işaret ediyorsa durdurur."""

    parsed = urlsplit(url)

    if parsed.hostname not in SAFE_TEST_HOSTS:
        raise RuntimeError(
            f"TEST_DATABASE_URL güvenli olmayan bir host'a işaret ediyor: {parsed.hostname!r}"
        )

    if "test" not in (parsed.path or "").lower():
        raise RuntimeError(
            "TEST_DATABASE_URL veritabanı adı 'test' içermiyor, production'a "
            "yanlışlıkla bağlanma riskine karşı reddedildi."
        )


def redact_database_url(url: str) -> str:
    """Bağlantı hatalarında şifrenin loglara sızmasını engeller."""

    return re.sub(r"//([^:/@]+):([^@]+)@", r"//\1:***@", url)


@contextmanager
def isolated_schema(engine: Engine):
    """Her test için ayrı bir schema açar, test bitince (hata olsa bile) siler."""

    schema_name = f"test_{uuid.uuid4().hex[:12]}"

    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    try:
        yield schema_name
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
