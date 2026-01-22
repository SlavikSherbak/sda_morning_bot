from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.conf import settings
from bot.handlers import start_router, messages_router, settings_router

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


async def setup_bot():
    dp.include_router(start_router)
    dp.include_router(settings_router)
    dp.include_router(messages_router)


async def start_bot():
    await setup_bot()
    await dp.start_polling(bot)


async def stop_bot():
    await bot.session.close()

