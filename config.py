"""
Configuration management
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # ==========================================
    # TELEGRAM
    # ==========================================

    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # ==========================================
    # DATABASE
    # ==========================================

    # PostgreSQL DATABASE_URL zorunlu
    DATABASE_URL = os.getenv("DATABASE_URL")

    # ==========================================
    # APPLICATION
    # ==========================================

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 900))  # 15 minutes
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", 8080))

    # ==========================================
    # SCRAPER
    # ==========================================

    GRANT_URL = (
        "https://www.firstinspires.org/programs/"
        "team-grant-opportunities"
    )

    REQUEST_TIMEOUT = 15

    # ==========================================
    # VALIDATION
    # ==========================================

    @staticmethod
    def validate():
        """Validate critical configuration"""

        if not Config.BOT_TOKEN:
            raise ValueError(
                "❌ TELEGRAM_BOT_TOKEN not set in environment variables"
            )

        if not Config.DATABASE_URL:
            raise ValueError(
                "❌ DATABASE_URL not set in environment variables"
            )

        return True


# ==========================================
# INITIALIZE CONFIG
# ==========================================

config = Config()
config.validate()