"""
Django management command для запуску Telegram бота.
"""
import asyncio
from django.core.management.base import BaseCommand
from bot.bot import start_bot


class Command(BaseCommand):
    help = "Запускає Telegram бота"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Запуск Telegram бота..."))
        try:
            asyncio.run(start_bot())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Бот зупинено користувачем"))







