"""
İzole PostgreSQL altyapısının kendisini doğrulayan testler
"""

import pytest
from sqlalchemy import text

from harness import guard_test_database_url, isolated_schema, redact_database_url


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


def test_redact_database_url_hides_password():
    redacted = redact_database_url(
        "postgresql://user:supersecret@localhost/itobot_test"
    )

    assert "supersecret" not in redacted
    assert "user:***@" in redacted
