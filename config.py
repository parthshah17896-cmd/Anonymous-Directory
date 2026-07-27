"""
===============================================================================
config.py
Telegram Directory Bot v2.0
===============================================================================

Loads application configuration from environment variables.

Compatible with:
    - Railway
    - Render
    - Local Development
===============================================================================
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

# Load .env file (ignored automatically on Railway if env vars are set)
load_dotenv()


@dataclass(frozen=True)
class Config:
    """
    Application configuration.
    """

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "10"))

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # -------------------------------------------------------------------------
    # Bot Settings
    # -------------------------------------------------------------------------

    BOT_NAME: str = os.getenv("BOT_NAME", "Telegram Directory Bot")

    ENABLE_PROFILE_CACHE: bool = (
        os.getenv("ENABLE_PROFILE_CACHE", "true").lower() == "true"
    )


config = Config()


def validate_config() -> None:
    """
    Validate required environment variables.
    """

    missing = []

    if not config.BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not config.DATABASE_URL:
        missing.append("DATABASE_URL")

    if config.ADMIN_ID == 0:
        missing.append("ADMIN_ID")

    if missing:
        raise RuntimeError(
            "Missing required environment variables:\n"
            + "\n".join(f"- {item}" for item in missing)
        )
