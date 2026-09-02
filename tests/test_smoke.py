"""
Ana modüllerin hatasız import edildiğini doğrulayan duman testleri
"""

import importlib


def test_config_imports():
    importlib.import_module("config")


def test_database_imports():
    importlib.import_module("database")


def test_scraper_imports():
    importlib.import_module("scraper")


def test_bot_imports():
    importlib.import_module("bot")
