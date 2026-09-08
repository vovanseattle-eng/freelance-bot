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
CATALOG_GIF_PATH: Path = ASSETS_DIR / "catalog.gif"
SEARCH_GIF_PATH: Path = ASSETS_DIR / "search.gif"
SETTINGS_GIF_PATH: Path = ASSETS_DIR / "settings.gif"
STATS_GIF_PATH: Path = ASSETS_DIR / "stats.gif"
CACHE_FILE: Path = ASSETS_DIR / "file_ids.json"

def get_cached_file_id(key: str) -> str | None:
    if CACHE_FILE.exists():
        try:
            import json
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return data.get(key)
        except Exception:
            pass
    return None

def save_cached_file_id(key: str, file_id: str) -> None:
    try:
        import json
        data = {}
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        data[key] = file_id
        CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
