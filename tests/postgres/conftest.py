"""
PostgreSQL entegrasyon testleri için ortak fixture'lar
"""

import os

import pytest
from sqlalchemy import create_engine

from harness import guard_test_database_url

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL tanımlı değil, PostgreSQL testleri atlanıyor",
        allow_module_level=True,
    )

guard_test_database_url(TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()
