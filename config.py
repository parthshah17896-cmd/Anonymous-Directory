import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Railway provides DATABASE_URL for Postgres.
# Postgres URLs on Railway often start with 'postgres://', which SQLAlchemy requires as 'postgresql://'
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/bot.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
