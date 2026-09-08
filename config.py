import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

TELEGRAM_API_ID_RAW = os.getenv("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_ID: int = int(TELEGRAM_API_ID_RAW) if TELEGRAM_API_ID_RAW.isdigit() else 0
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "").strip()

RSS_POLL_INTERVAL: int = int(os.getenv("RSS_POLL_INTERVAL", "60"))
DATABASE_PATH: str = str(BASE_DIR / os.getenv("DATABASE_PATH", "freelance_orders.db"))
SESSION_NAME: str = str(BASE_DIR / "userbot_session")
TELEGRAM_PROXY: str = os.getenv("TELEGRAM_PROXY", "").strip()

ASSETS_DIR: Path = BASE_DIR / "assets"
MENU_GIF_PATH: Path = ASSETS_DIR / "menu.gif"
NOTIF_GIF_PATH: Path = ASSETS_DIR / "notification.gif"
