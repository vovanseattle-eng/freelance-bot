from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.emoji import E

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

def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Лента заказов", callback_data="feed_menu", icon_custom_emoji_id=E.FILE)
    b.button(text="Поиск", callback_data="search_prompt", icon_custom_emoji_id=E.SEARCH)
    b.button(text="Уведомления", callback_data="settings", icon_custom_emoji_id=E.BELL)
    b.button(text="Статистика", callback_data="stats", icon_custom_emoji_id=E.STATS)
    b.adjust(1)
    return b.as_markup()

def feed_categories_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Все направления", callback_data="feed:all:0", icon_custom_emoji_id=E.JOB)
    for code, name in CATEGORY_NAMES.items():
        b.button(text=name, callback_data=f"feed:{code}:0", icon_custom_emoji_id=CATEGORY_EMOJIS[code])
    b.button(text="Назад", callback_data="menu", icon_custom_emoji_id=E.BACK)
    b.adjust(1)
    return b.as_markup()

def order_card_kb(link: str, category: str, offset: int, total: int, contact: Optional[str] = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    if contact:
        clean_contact = contact.lstrip("@")
        b.button(
            text=f"Откликнуться (@{clean_contact})",
            url=f"https://t.me/{clean_contact}",
            icon_custom_emoji_id=E.PROFILE,
        )
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)
    else:
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)

    nav_buttons = []
    if offset > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Ранее",
                callback_data=f"feed:{category}:{offset - 1}",
                icon_custom_emoji_id=E.NAV,
            )
        )
    if offset + 1 < total:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Далее",
                callback_data=f"feed:{category}:{offset + 1}",
                icon_custom_emoji_id=E.NAV,
            )
        )
    if nav_buttons:
        b.row(*nav_buttons)

    b.button(text="К направлениям", callback_data="feed_menu", icon_custom_emoji_id=E.JOB)
    b.adjust(1)
    return b.as_markup()

def settings_kb(selected_cats: List[str], notifications_enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    notif_text = "Уведомления: Включены" if notifications_enabled else "Уведомления: Выключены"
    notif_icon = E.CHECK if notifications_enabled else E.CROSS
    b.button(text=notif_text, callback_data="toggle_notif", icon_custom_emoji_id=notif_icon)

    for code, name in CATEGORY_NAMES.items():
        is_active = code in selected_cats
        status_label = " [ON]" if is_active else " [OFF]"
        b.button(
            text=f"{name}{status_label}",
            callback_data=f"toggle_cat:{code}",
            icon_custom_emoji_id=CATEGORY_EMOJIS[code],
        )

    b.button(text="Назад", callback_data="menu", icon_custom_emoji_id=E.BACK)
    b.adjust(1)
    return b.as_markup()

def back_to_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="menu", icon_custom_emoji_id=E.BACK)
    return b.as_markup()

def push_order_kb(link: str, contact: Optional[str] = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if contact:
        clean_contact = contact.lstrip("@")
        b.button(
            text=f"Откликнуться (@{clean_contact})",
            url=f"https://t.me/{clean_contact}",
            icon_custom_emoji_id=E.PROFILE,
        )
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)
    else:
        b.button(text="Источник", url=link, icon_custom_emoji_id=E.LINK)
    b.adjust(1)
    return b.as_markup()
