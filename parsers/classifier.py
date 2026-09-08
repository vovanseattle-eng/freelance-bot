import re
from typing import Optional

DEV_KEYWORDS = {
    "python", "бот", "bot", "django", "fastapi", "flask", "aiogram", "telethon",
    "javascript", "typescript", "react", "vue", "node", "backend", "frontend",
    "html", "css", "сайт", "скрипт", "парсер", "парсинг", "база данных", "sql",
    "php", "laravel", "wordpress", "1c", "1с", "разработчик", "программист",
    "api", "веб-сайт", "вёрстка", "верстка", "fullstack", "mobile", "flutter", "ios", "android",
    "qa", "тестировщик", "devops", "docker", "linux", "golang", "java", "c#", "c++", "unity"
}

DESIGN_KEYWORDS = {
    "дизайн", "дизайнер", "figma", "фигма", "логотип", "баннер", "баннеры", "инфографика",
    "карточки", "wildberries", "wb", "ozon", "озон", "ui", "ux", "ui/ux", "веб-дизайн",
    "photoshop", "illustrator", "3d", "blender", "макет", "редизайн", "креатив", "креативы",
    "полиграфия", "иллюстрация", "айдентика", "брендбук", "оформление", "типографика"
}

SMM_KEYWORDS = {
    "smm", "смм", "маркетинг", "таргет", "таргетолог", "продвижение", "трафик",
    "reels", "рилс", "сторис", "stories", "ведение канала", "телеграм-канал",
    "контент-план", "инстаграм", "instagram", "вк", "vk", "директ", "закупка рекламы",
    "посевы", "трафик-менеджер", "маркетолог", "seo", "контекстолог", "директолог"
}

COPYWRITING_KEYWORDS = {
    "текст", "тексты", "копирайтер", "копирайтинг", "статья", "статьи", "рерайт",
    "рерайтинг", "пост", "посты", "seo-текст", "сценарий", "редактор", "корректор",
    "переводчик", "перевод", "описание товаров", "написание"
}

VIDEO_KEYWORDS = {
    "видео", "монтаж", "видеомонтаж", "видеомонтажер", "монтажер", "shorts", "шортс",
    "youtube", "ютуб", "premiere", "after effects", "capcut", "анимация",
    "motion", "моушн", "субтитры", "озвучка", "диктор", "sound"
}

OFFLINE_OR_SPAM_WORDS = [
    "администратор", "салон", "ресторан", "отель", "гостиниц", "официант", "бармен",
    "повар", "курьер", "водитель", "продавец", "кассир", "уборщиц", "клининг",
    "склад", "пункт выдачи", "пвз", "охранник", "няня", "сиделка", "массаж",
    "мастер маникюра", "бровист", "грузчик", "автомойщик", "сантехник", "электрик",
    "заработок от", "удаленная работа без опыта", "от 18 лет", "казино", "ставки",
    "1win", "криптосигнал", "накрутка", "только москва офлайн", "работа в офисе москв"
]

EXCLUDED_CHANNELS = {
    "freelancetaverna", "distantsiya", "normrabota", "forfreelancers",
    "smm_vacancies", "design_jobs", "it_vacancies", "work_in_media", "vdhl_good",
    "tproger_jobs", "forwebdev", "mobile_jobs", "qa_jobs", "devs_jobs", "jobgeeks"
}

def is_it_job(title: str, text: str) -> bool:
    """Проверяет, что вакансия относится к IT / Digital / Freelance, а не к офлайн-работе."""
    combined = f"{title.lower()} {text.lower()}"
    
    # 1. Проверка на офлайн-профессии и спам
    for stop_word in OFFLINE_OR_SPAM_WORDS:
        # Исключаем ложные срабатывания (например, системный администратор — это IT)
        if stop_word == "администратор" and ("системный" in combined or "баз данных" in combined or "linux" in combined):
            continue
        if stop_word in combined:
            return False
            
    return True

def classify_text(title: str, text: str) -> Optional[str]:
    """Классифицирует текст только по IT-направлениям. Возвращает None, если вакансия не из IT."""
    if not is_it_job(title, text):
        return None

    combined = f"{title.lower()} {text.lower()}"
    words = set(re.findall(r"[a-zа-яё0-9/_-]+", combined))

    scores = {
        "dev": len(words & DEV_KEYWORDS),
        "design": len(words & DESIGN_KEYWORDS),
        "smm": len(words & SMM_KEYWORDS),
        "copywriting": len(words & COPYWRITING_KEYWORDS),
        "video": len(words & VIDEO_KEYWORDS),
    }

    title_words = set(re.findall(r"[a-zа-яё0-9/_-]+", title.lower()))
    scores["dev"] += len(title_words & DEV_KEYWORDS) * 2
    scores["design"] += len(title_words & DESIGN_KEYWORDS) * 2
    scores["smm"] += len(title_words & SMM_KEYWORDS) * 2
    scores["copywriting"] += len(title_words & COPYWRITING_KEYWORDS) * 2
    scores["video"] += len(title_words & VIDEO_KEYWORDS) * 2

    best_cat, best_score = max(scores.items(), key=lambda x: x[1])
    # Только если есть четкое совпадение с IT-ключевиками
    return best_cat if best_score >= 1 else None

def extract_budget(text: str) -> str:
    match = re.search(
        r"(?:бюджет|оплата|цена|стоимость|зп|ставка)?\s*[:\-–]?\s*(\d[\d\s]{2,8}\s*(?:руб|р\.|₽|usd|\$|usdt|byn|kzt|uah|€|евро))",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return "По договоренности"

def extract_tg_contact(text: str) -> Optional[str]:
    """Извлекает прямой юзернейм Telegram заказчика для отклика."""
    # Поиск t.me/username
    links = re.findall(r"t\.me/([a-zA-Z0-9_]{5,32})", text, re.IGNORECASE)
    for lk in links:
        if lk.lower() not in EXCLUDED_CHANNELS and not lk.startswith("joinchat") and not lk.startswith("c/"):
            return lk

    # Поиск @username
    tags = re.findall(r"@([a-zA-Z0-9_]{5,32})", text)
    for tg in tags:
        if tg.lower() not in EXCLUDED_CHANNELS:
            return tg

    return None
