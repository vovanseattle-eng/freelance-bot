from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaAnimation, FSInputFile

from bot.emoji import E, title
from bot.keyboards import settings_kb
from database import repository
import config

router = Router()

@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery) -> None:
    try:
        user = await repository.get_user(call.from_user.id)
        if not user:
            await repository.upsert_user(call.from_user.id, call.from_user.username, call.from_user.first_name)
            user = await repository.get_user(call.from_user.id)

        raw_cats = (user.get("categories") or "") if user else ""
        cats = [c.strip() for c in raw_cats.split(",") if c.strip()]
        notif_enabled = bool(user.get("notifications_enabled", 1)) if user else True

        text = (
            f"{title(E.BELL, 'Настройка уведомлений')}\n\n"
            f"Выберите IT категории, по которым хотите мгновенно получать новые заказы:"
        )
        if not call.message:
            return

        settings_id = config.get_cached_file_id("settings")
        if call.message.animation or call.message.photo or call.message.video:
            if settings_id:
                try:
                    await call.message.edit_media(
                        media=InputMediaAnimation(media=settings_id, caption=text, parse_mode="HTML"),
                        reply_markup=settings_kb(cats, notif_enabled),
                    )
                    return
                except Exception:
                    pass
            await call.message.edit_caption(
                caption=text,
                reply_markup=settings_kb(cats, notif_enabled),
                parse_mode="HTML",
            )
        else:
            if settings_id:
                try:
                    await call.message.delete()
                except Exception:
                    pass
                await call.message.answer_animation(
                    animation=settings_id,
                    caption=text,
                    reply_markup=settings_kb(cats, notif_enabled),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(
                    text,
                    reply_markup=settings_kb(cats, notif_enabled),
                    parse_mode="HTML",
                )
    finally:
        await call.answer()

@router.callback_query(F.data == "toggle_notif")
async def cb_toggle_notif(call: CallbackQuery) -> None:
    try:
        new_state = await repository.toggle_notifications(call.from_user.id)
        user = await repository.get_user(call.from_user.id)
        raw_cats = (user.get("categories") or "") if user else ""
        cats = [c.strip() for c in raw_cats.split(",") if c.strip()]

        text = (
            f"{title(E.BELL, 'Настройка уведомлений')}\n\n"
            f"Статус уведомлений обновлен."
        )
        if call.message:
            if call.message.animation or call.message.photo or call.message.video:
                await call.message.edit_caption(
                    caption=text,
                    reply_markup=settings_kb(cats, new_state),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(
                    text,
                    reply_markup=settings_kb(cats, new_state),
                    parse_mode="HTML",
                )
    finally:
        await call.answer("Сохранено")

@router.callback_query(F.data.startswith("toggle_cat:"))
async def cb_toggle_cat(call: CallbackQuery) -> None:
    try:
        category = call.data.split(":")[1]
        user = await repository.get_user(call.from_user.id)
        raw_cats = (user.get("categories") or "") if user else ""
        cats = set(c.strip() for c in raw_cats.split(",") if c.strip())

        if category in cats:
            cats.remove(category)
        else:
            cats.add(category)

        await repository.update_user_categories(call.from_user.id, list(cats))
        notif_enabled = bool(user.get("notifications_enabled", 1)) if user else True

        text = (
            f"{title(E.BELL, 'Настройка уведомлений')}\n\n"
            f"Список активных направлений обновлен."
        )
        if call.message:
            if call.message.animation or call.message.photo or call.message.video:
                await call.message.edit_caption(
                    caption=text,
                    reply_markup=settings_kb(list(cats), notif_enabled),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(
                    text,
                    reply_markup=settings_kb(list(cats), notif_enabled),
                    parse_mode="HTML",
                )
    finally:
        await call.answer("Обновлено")
