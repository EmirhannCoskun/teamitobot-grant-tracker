"""
Test ortamı için gerekli environment değişkenlerini sağlar
"""

import os

# These values intentionally replace ambient credentials before application imports.
# The reserved .invalid host cannot resolve to a production or staging database.
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token-not-a-real-credential"
os.environ["DATABASE_URL"] = "postgresql://test:test@database.invalid:5432/itobot_test"
os.environ["ENVIRONMENT"] = "test"
