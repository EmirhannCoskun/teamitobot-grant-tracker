"""Production cutover: doğrula ve baseline'a stamp'le.

`DATABASE_URL=<production-url> alembic stamp head` çıplak haliyle riskli:
production şeması ile baseline migration'ın (9ffc96b8fba3) beklediği şema
arasında kolon/type/nullable/constraint/index farkı varsa fark edilmeden
yanlış revizyon işaretlenmiş olur. Bu script önce gerçek şemayı
EXPECTED_SCHEMA sözleşmesiyle karşılaştırır, eşleşmiyorsa hiçbir şey
yazmadan durur; eşleşiyorsa `alembic stamp head` çalıştırır.

EXPECTED_SCHEMA, database.py'deki ORM modellerinden DEĞİL, doğrudan
alembic/versions/9ffc96b8fba3_*.py migration dosyasından elle çıkarılmıştır
(bkz. tests/postgres/test_schema_contract.py, sözleşmeyi ORM'den bağımsız
olarak gerçek bir migration çalıştırmasına karşı doğrular).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Inspector

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SCHEMA = {
    "users": {
        "columns": {
            "id": {"type": "INTEGER", "nullable": False},
            "chat_id": {"type": "BIGINT", "nullable": False},
            "username": {"type": "VARCHAR(255)", "nullable": True},
            "is_active": {"type": "BOOLEAN", "nullable": True},
            "is_subscribed": {"type": "BOOLEAN", "nullable": True},
            "total_scrapes": {"type": "INTEGER", "nullable": False},
            "created_at": {"type": "TIMESTAMP", "nullable": True},
        },
        "primary_key": ("id",),
        "unique_constraints": frozenset(),
        "foreign_keys": frozenset(),
        "unique_indexes": frozenset({("chat_id",)}),
    },
    "grants": {
        "columns": {
            "id": {"type": "INTEGER", "nullable": False},
            "text": {"type": "VARCHAR(1000)", "nullable": True},
            "title": {"type": "VARCHAR(1000)", "nullable": True},
            "start_date": {"type": "DATE", "nullable": True},
            "end_date": {"type": "DATE", "nullable": True},
            "url": {"type": "VARCHAR(2000)", "nullable": True},
            "detected_at": {"type": "TIMESTAMP", "nullable": True},
        },
        "primary_key": ("id",),
        "unique_constraints": frozenset(),
        "foreign_keys": frozenset(),
        "unique_indexes": frozenset(),
    },
    "notifications": {
        "columns": {
            "id": {"type": "INTEGER", "nullable": False},
            "user_id": {"type": "INTEGER", "nullable": False},
            "grant_id": {"type": "INTEGER", "nullable": False},
            "sent_at": {"type": "TIMESTAMP", "nullable": True},
        },
        "primary_key": ("id",),
        "unique_constraints": frozenset({("grant_id", "user_id")}),
        "foreign_keys": frozenset(
            {
                ("grant_id", "grants", "id"),
                ("user_id", "users", "id"),
            }
        ),
        "unique_indexes": frozenset(),
    },
    "stats": {
        "columns": {
            "id": {"type": "INTEGER", "nullable": False},
            "total_scrapes": {"type": "INTEGER", "nullable": True},
            "total_notifications": {"type": "INTEGER", "nullable": True},
            "total_users": {"type": "INTEGER", "nullable": True},
            "started_at": {"type": "TIMESTAMP", "nullable": True},
            "last_scrape_at": {"type": "TIMESTAMP", "nullable": True},
        },
        "primary_key": ("id",),
        "unique_constraints": frozenset(),
        "foreign_keys": frozenset(),
        "unique_indexes": frozenset(),
    },
}


def describe_actual_schema(inspector: Inspector, table_names) -> dict:
    """Verilen tablolar için gerçek veritabanı şemasını EXPECTED_SCHEMA ile
    aynı şekilde tanımlar."""

    schema = {}
    for table_name in table_names:
        columns = {
            col["name"]: {"type": str(col["type"]), "nullable": col["nullable"]}
            for col in inspector.get_columns(table_name)
        }
        primary_key = tuple(
            inspector.get_pk_constraint(table_name)["constrained_columns"] or []
        )
        unique_constraints = frozenset(
            tuple(sorted(unique["column_names"]))
            for unique in inspector.get_unique_constraints(table_name)
        )
        foreign_keys = frozenset(
            (
                fk["constrained_columns"][0],
                fk["referred_table"],
                fk["referred_columns"][0],
            )
            for fk in inspector.get_foreign_keys(table_name)
        )
        # Bir unique constraint'in arkasındaki otomatik index'i ayrı bir
        # unique index gibi saymamak için dışarıda bırakıyoruz.
        unique_indexes = frozenset(
            tuple(index["column_names"])
            for index in inspector.get_indexes(table_name)
            if index["unique"] and not index.get("duplicates_constraint")
        )

        schema[table_name] = {
            "columns": columns,
            "primary_key": primary_key,
            "unique_constraints": unique_constraints,
            "foreign_keys": foreign_keys,
            "unique_indexes": unique_indexes,
        }
    return schema


def diff_schema(expected: dict, actual: dict) -> list[str]:
    """İki şema tanımını karşılaştırır, insan tarafından okunabilir fark
    listesi döner (production verisi/URL'i içermez). Boş liste = eşleşiyor."""

    mismatches = []

    for table_name, expected_table in expected.items():
        if table_name not in actual:
            mismatches.append(f"tablo eksik: {table_name}")
            continue

        actual_table = actual[table_name]

        for column_name, expected_column in expected_table["columns"].items():
            actual_column = actual_table["columns"].get(column_name)
            if actual_column is None:
                mismatches.append(f"{table_name}.{column_name}: kolon eksik")
                continue
            if actual_column["type"] != expected_column["type"]:
                mismatches.append(
                    f"{table_name}.{column_name}: type beklenen="
                    f"{expected_column['type']} gerçek={actual_column['type']}"
                )
            if actual_column["nullable"] != expected_column["nullable"]:
                mismatches.append(
                    f"{table_name}.{column_name}: nullable beklenen="
                    f"{expected_column['nullable']} gerçek={actual_column['nullable']}"
                )

        extra_columns = set(actual_table["columns"]) - set(expected_table["columns"])
        for column_name in sorted(extra_columns):
            mismatches.append(f"{table_name}.{column_name}: beklenmeyen ekstra kolon")

        if actual_table["primary_key"] != expected_table["primary_key"]:
            mismatches.append(
                f"{table_name}: primary key beklenen={expected_table['primary_key']} "
                f"gerçek={actual_table['primary_key']}"
            )
        if actual_table["unique_constraints"] != expected_table["unique_constraints"]:
            mismatches.append(
                f"{table_name}: unique constraint uyuşmuyor "
                f"(beklenen={sorted(expected_table['unique_constraints'])}, "
                f"gerçek={sorted(actual_table['unique_constraints'])})"
            )
        if actual_table["foreign_keys"] != expected_table["foreign_keys"]:
            mismatches.append(
                f"{table_name}: foreign key uyuşmuyor "
                f"(beklenen={sorted(expected_table['foreign_keys'])}, "
                f"gerçek={sorted(actual_table['foreign_keys'])})"
            )
        if actual_table["unique_indexes"] != expected_table["unique_indexes"]:
            mismatches.append(
                f"{table_name}: unique index uyuşmuyor "
                f"(beklenen={sorted(expected_table['unique_indexes'])}, "
                f"gerçek={sorted(actual_table['unique_indexes'])})"
            )

    for table_name in set(actual) - set(expected):
        mismatches.append(f"beklenmeyen ekstra tablo: {table_name}")

    return mismatches


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL tanımlı değil.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(REPOSITORY_ROOT))
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "schema-verify-tooling-placeholder")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        actual = describe_actual_schema(inspector, EXPECTED_SCHEMA.keys())
    finally:
        engine.dispose()

    mismatches = diff_schema(EXPECTED_SCHEMA, actual)
    if mismatches:
        print("❌ Şema baseline ile eşleşmiyor, stamp uygulanmadı:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  - {mismatch}", file=sys.stderr)
        return 1

    print("✅ Şema baseline ile eşleşiyor, 'alembic stamp head' uygulanıyor...")

    from alembic.config import Config

    from alembic import command

    os.environ["_ALEMBIC_DATABASE_URL"] = database_url
    alembic_cfg = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(REPOSITORY_ROOT / "alembic"))
    command.stamp(alembic_cfg, "head")

    print("✅ Stamp tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
