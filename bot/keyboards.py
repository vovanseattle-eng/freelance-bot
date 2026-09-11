from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.emoji import E

BLUE = "primary"

CATEGORY_NAMES = {
    "dev": "Разработка и IT",
    "design": "Дизайн и UI/UX",
    "smm": "Маркетинг и SMM",
    "copywriting": "Копирайтинг",
    "video": "Видеомонтаж",
}

CATEGORY_EMOJIS = {
    "dev": E.CODE,
    "design": E.DESIGN,
    "smm": E.SMM,
    "copywriting": E.WRITE,
    "video": E.MEDIA,
}


def _b(
    builder: InlineKeyboardBuilder,
    text: str,
    data: str,
    icon: E,
    *,
    style: str | None = None,
) -> None:
    builder.button(text=text, callback_data=data, icon_custom_emoji_id=icon, style=style)


def _back(builder: InlineKeyboardBuilder, data: str = "menu") -> None:
    _b(builder, "Назад", data, E.BACK)


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _b(b, "Лента заказов", "feed_menu", E.FIRE, style=BLUE)
    _b(b, "Поиск", "search_prompt", E.SEARCH, style=BLUE)
    _b(b, "Уведомления", "settings", E.BELL)
    _b(b, "Статистика", "stats", E.STATS)
    b.adjust(1, 1, 2)
    return b.as_markup()


def feed_categories_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _b(b, "Все направления", "feed:all:0", E.JOB, style=BLUE)
    for code, name in CATEGORY_NAMES.items():
        _b(b, name, f"feed:{code}:0", CATEGORY_EMOJIS[code])
    _back(b, "menu")
    b.adjust(1)
    return b.as_markup()


def order_card_kb(
    link: str,
    category: str,
    offset: int,
    total: int,
    contact: Optional[str] = None,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    adjust_pattern = []

    if contact:
        clean_contact = contact.lstrip("@")
        b.button(
            text=f"Откликнуться (@{clean_contact})",
            url=f"https://t.me/{clean_contact}",
            icon_custom_emoji_id=E.PROFILE,
            style=BLUE,
        )
        adjust_pattern.append(1)
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)
        adjust_pattern.append(1)
    else:
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK, style=BLUE)
        adjust_pattern.append(1)

    nav_count = 0
    if offset > 0:
        b.button(text="Ранее", callback_data=f"feed:{category}:{offset - 1}", icon_custom_emoji_id=E.NAV)
        nav_count += 1
    if offset + 1 < total:
        b.button(text="Далее", callback_data=f"feed:{category}:{offset + 1}", icon_custom_emoji_id=E.NAV)
        nav_count += 1
    if nav_count > 0:
        adjust_pattern.append(nav_count)

    _b(b, "К направлениям", "feed_menu", E.JOB)
    adjust_pattern.append(1)

    b.adjust(*adjust_pattern)
    return b.as_markup()


def settings_kb(selected_cats: List[str], notifications_enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    notif_text = "Уведомления: Включены" if notifications_enabled else "Уведомления: Выключены"
    notif_icon = E.CHECK if notifications_enabled else E.CROSS
    _b(b, notif_text, "toggle_notif", notif_icon, style=BLUE)

    for code, name in CATEGORY_NAMES.items():
        is_active = code in selected_cats
        status_label = " [ON]" if is_active else " [OFF]"
        _b(
            b,
            f"{name}{status_label}",
            f"toggle_cat:{code}",
            CATEGORY_EMOJIS[code],
        )

    _back(b, "menu")
    b.adjust(1)
    return b.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _back(b, "menu")
    return b.as_markup()


def push_order_kb(link: str, contact: Optional[str] = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if contact:
        clean_contact = contact.lstrip("@")
        b.button(
            text=f"Откликнуться (@{clean_contact})",
            url=f"https://t.me/{clean_contact}",
            icon_custom_emoji_id=E.PROFILE,
            style=BLUE,
        )
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)
    else:
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK, style=BLUE)
    b.adjust(1)
    return b.as_markup()

