"""
Configuration management
"""
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    """Application configuration"""
    
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///grant_tracker.db")
    
    # Application
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 900))  # 15 minutes
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", 8080))
    
    # Scraper
    GRANT_URL = "https://www.firstinspires.org/programs/team-grant-opportunities"
    REQUEST_TIMEOUT = 15
    
    @staticmethod
    def validate():
        """Validate critical config"""
        if not Config.BOT_TOKEN:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN not set in .env")
        return True

# Initialize config
config = Config()
config.validate()