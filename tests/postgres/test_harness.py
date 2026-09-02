"""
İzole PostgreSQL altyapısının kendisini doğrulayan testler
"""

import pytest
from sqlalchemy import create_engine, text

from harness import (
    connect_or_raise,
    guard_test_database_url,
    isolated_schema,
    redact_database_url,
)


def test_connectivity(pg_engine):
    with pg_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1


def test_schema_isolation(pg_engine):
    with isolated_schema(pg_engine) as schema_a:
        with pg_engine.begin() as connection:
            connection.execute(text(f'CREATE TABLE "{schema_a}".marker (id int)'))
            connection.execute(text(f'INSERT INTO "{schema_a}".marker VALUES (1)'))

        with isolated_schema(pg_engine) as schema_b:
            with pg_engine.connect() as connection:
                tables = connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = :schema"
                    ),
                    {"schema": schema_b},
                ).fetchall()

            assert tables == []


def test_teardown_runs_after_failure(pg_engine):
    schema_name = None

    with pytest.raises(RuntimeError):
        with isolated_schema(pg_engine) as schema:
            schema_name = schema
            raise RuntimeError("kasitli hata")

    with pg_engine.connect() as connection:
        remaining = connection.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = :name"
            ),
            {"name": schema_name},
        ).fetchone()

    assert remaining is None


def test_guard_rejects_non_test_host():
    with pytest.raises(RuntimeError):
        guard_test_database_url("postgresql://user:pass@prod-db.render.com/itobot")


def test_guard_rejects_non_test_database_name():
    with pytest.raises(RuntimeError):
        guard_test_database_url("postgresql://user:pass@localhost/itobot")


@pytest.mark.parametrize("database_name", ["latest", "contest"])
def test_guard_rejects_test_lookalike_names(database_name):
    with pytest.raises(RuntimeError):
        guard_test_database_url(f"postgresql://user:pass@localhost/{database_name}")


def test_redact_database_url_hides_password():
    redacted = redact_database_url(
        "postgresql://user:supersecret@localhost/itobot_test"
    )

    assert "supersecret" not in redacted
    assert "user:***@" in redacted


def test_redact_database_url_hides_query_string_password():
    redacted = redact_database_url(
        "postgresql://localhost/itobot_test?sslpassword=supersecret"
    )

    assert "supersecret" not in redacted
    assert "sslpassword=***" in redacted


def test_redact_database_url_hides_password_with_empty_username():
    redacted = redact_database_url("postgresql://:supersecret@localhost:1/itobot_test")

    assert "supersecret" not in redacted


def test_connect_or_raise_redacts_credentials_on_failure():
    bad_url = "postgresql://user:supersecret@localhost:1/itobot_test"
    bad_engine = create_engine(bad_url)

    with pytest.raises(RuntimeError) as excinfo:
        connect_or_raise(bad_engine, bad_url)

    assert "supersecret" not in str(excinfo.value)


def test_connect_or_raise_redacts_password_with_empty_username():
    bad_url = "postgresql://:supersecret@localhost:1/itobot_test"
    bad_engine = create_engine(bad_url)

    with pytest.raises(RuntimeError) as excinfo:
        connect_or_raise(bad_engine, bad_url)

    assert "supersecret" not in str(excinfo.value)
