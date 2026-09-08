"""
Alembic baseline'ının gerçek PostgreSQL'e karşı davranışını doğrulayan testler
"""

import os
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from alembic import command
from database import Base

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _maintenance_url(test_database_url):
    return test_database_url.rsplit("/", 1)[0] + "/postgres"


def _create_scratch_database(test_database_url):
    name = f"itobot_alembic_{uuid.uuid4().hex[:12]}"
    engine = create_engine(
        _maintenance_url(test_database_url), isolation_level="AUTOCOMMIT"
    )
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        engine.dispose()
    return test_database_url.rsplit("/", 1)[0] + f"/{name}"


def _drop_scratch_database(test_database_url, database_url):
    name = database_url.rsplit("/", 1)[1]
    engine = create_engine(
        _maintenance_url(test_database_url), isolation_level="AUTOCOMMIT"
    )
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        engine.dispose()


def _alembic_config(database_url):
    config = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
    os.environ["_ALEMBIC_DATABASE_URL"] = database_url
    return config


def test_empty_database_upgrade_recreates_baseline_schema(pg_engine):
    scratch_url = _create_scratch_database(TEST_DATABASE_URL)
    try:
        command.upgrade(_alembic_config(scratch_url), "head")

        engine = create_engine(scratch_url)
        try:
            with engine.connect() as connection:
                tables = (
                    connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = 'public'"
                        )
                    )
                    .scalars()
                    .all()
                )
        finally:
            engine.dispose()

        assert {"users", "grants", "notifications", "stats"} <= set(tables)
    finally:
        _drop_scratch_database(TEST_DATABASE_URL, scratch_url)


def test_upgrade_produces_no_further_orm_diff(pg_engine):
    """Baseline uygulandıktan sonra autogenerate hiçbir fark bulmamalı
    (baseline, database.py'deki ORM modelleriyle birebir eşleşiyor)."""

    scratch_url = _create_scratch_database(TEST_DATABASE_URL)
    try:
        command.upgrade(_alembic_config(scratch_url), "head")

        engine = create_engine(scratch_url)
        try:
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                diff = compare_metadata(context, Base.metadata)
        finally:
            engine.dispose()

        assert diff == []
    finally:
        _drop_scratch_database(TEST_DATABASE_URL, scratch_url)


def test_legacy_create_all_database_can_be_stamped_without_rerunning_ddl(pg_engine):
    """create_all() ile önceden oluşturulmuş (Alembic'ten habersiz) bir
    veritabanı, DDL tekrar çalıştırılmadan baseline'a stamp'lenebilmeli."""

    scratch_url = _create_scratch_database(TEST_DATABASE_URL)
    try:
        legacy_engine = create_engine(scratch_url)
        try:
            Base.metadata.create_all(bind=legacy_engine)
        finally:
            legacy_engine.dispose()

        config = _alembic_config(scratch_url)
        command.stamp(config, "head")

        # Stamp sonrası upgrade hiçbir DDL çalıştırmadan sessizce tamamlanmalı.
        command.upgrade(config, "head")

        engine = create_engine(scratch_url)
        try:
            with engine.connect() as connection:
                version = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar()
        finally:
            engine.dispose()

        assert version is not None
    finally:
        _drop_scratch_database(TEST_DATABASE_URL, scratch_url)


def test_baseline_downgrade_is_refused(pg_engine):
    """ADR-004 geregi baseline downgrade'i yikici oldugu icin reddedilmeli,
    tablolar silinmemeli."""

    scratch_url = _create_scratch_database(TEST_DATABASE_URL)
    try:
        config = _alembic_config(scratch_url)
        command.upgrade(config, "head")

        with pytest.raises(Exception, match="ADR-004"):
            command.downgrade(config, "base")

        engine = create_engine(scratch_url)
        try:
            with engine.connect() as connection:
                tables = (
                    connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = 'public'"
                        )
                    )
                    .scalars()
                    .all()
                )
        finally:
            engine.dispose()

        assert {"users", "grants", "notifications", "stats"} <= set(tables)
    finally:
        _drop_scratch_database(TEST_DATABASE_URL, scratch_url)
