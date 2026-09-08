"""
Скрипт первичной авторизации второго Telegram-аккаунта (юзербота).
Запускается один раз в консоли: python setup_userbot.py
"""
import asyncio
from telethon import TelegramClient
import config

async def main():
    print("=== Авторизация второго аккаунта Telegram ===")
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        print("Ошибка: Заполните TELEGRAM_API_ID и TELEGRAM_API_HASH в файле .env!")
        print("Получить их можно бесплатно за 1 минуту на https://my.telegram.org -> API development tools")
        return

    phone = config.TELEGRAM_PHONE or input("Введите номер телефона второго аккаунта (например, +79991234567): ").strip()
    client = TelegramClient(config.SESSION_NAME, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)

    await client.start(phone=phone)
    me = await client.get_me()
    print(f"\nУспешно авторизован аккаунт: {me.first_name} (@{me.username or 'без юзернейма'}) [ID: {me.id}]")
    print(f"Файл сессии сохранен как: {config.SESSION_NAME}.session")
    print("Теперь юзербот готов слушать каналы и чаты в фоне!")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
