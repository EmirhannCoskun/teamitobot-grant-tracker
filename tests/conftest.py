"""
Test ortamı için gerekli environment değişkenlerini sağlar
"""

import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
