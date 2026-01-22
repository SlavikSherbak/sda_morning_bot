"""
Models for storing books and daily inspirations.
"""
from django.db import models
from django.contrib.auth.models import User
from timezone_field import TimeZoneField

from core.constants import LANGUAGE_CHOICES


class Book(models.Model):
    """Book with morning readings."""
    title = models.CharField(max_length=500, verbose_name="Title")
    source_url = models.URLField(blank=True, null=True, verbose_name="Source URL")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="uk",
        verbose_name="Language"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_parsed = models.BooleanField(default=False, verbose_name="Parsed")
    last_parsed_at = models.DateTimeField(blank=True, null=True, verbose_name="Last parsed at")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class DailyInspiration(models.Model):
    """Daily inspiration from a book."""
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="daily_inspirations",
        verbose_name="Book"
    )
    date = models.DateField(db_index=True, verbose_name="Date")
    paragraph_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Paragraph ID"
    )
    original_text = models.TextField(verbose_name="Original text")
    html_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="HTML content"
    )
    translation_ukrainian = models.TextField(
        blank=True,
        null=True,
        verbose_name="Ukrainian translation"
    )
    translation_russian = models.TextField(
        blank=True,
        null=True,
        verbose_name="Russian translation"
    )
    translation_english = models.TextField(
        blank=True,
        null=True,
        verbose_name="English translation"
    )
    source_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Source URL"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Daily inspiration"
        verbose_name_plural = "Daily inspirations"
        ordering = ["-date", "book"]
        unique_together = [("book", "date")]

    def __str__(self) -> str:
        return f"{self.book.title} - {self.date}"

    def get_text_by_language(self, language: str) -> str:
        """Get inspiration text in specified language."""
        if language == "uk" and self.translation_ukrainian:
            return self.translation_ukrainian
        elif language == "ru" and self.translation_russian:
            return self.translation_russian
        elif language == "en" and self.translation_english:
            return self.translation_english
        else:
            return self.original_text


class TelegramUser(models.Model):
    """Telegram user."""
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="First name")
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Last name")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="telegram_user"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Telegram user"
        verbose_name_plural = "Telegram users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}"
        return f"User {self.telegram_id}"


class UserSettings(models.Model):
    """User settings."""
    telegram_user = models.OneToOneField(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name="Telegram user"
    )
    notification_time = models.TimeField(verbose_name="Notification time")
    timezone = TimeZoneField(
        default="Europe/Kyiv",
        verbose_name="Timezone"
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="uk",
        verbose_name="Language"
    )
    selected_book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="user_settings",
        verbose_name="Selected book"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "User settings"
        verbose_name_plural = "User settings"

    def __str__(self) -> str:
        return f"Settings for {self.telegram_user}"


class SentInspiration(models.Model):
    """Sent inspiration to user."""
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="sent_inspirations",
        verbose_name="Telegram user"
    )
    inspiration = models.ForeignKey(
        DailyInspiration,
        on_delete=models.CASCADE,
        related_name="sent_to_users",
        verbose_name="Inspiration"
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        verbose_name="Language"
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Sent at")

    class Meta:
        verbose_name = "Sent inspiration"
        verbose_name_plural = "Sent inspirations"
        ordering = ["-sent_at"]
        unique_together = [("telegram_user", "inspiration", "language")]

    def __str__(self) -> str:
        return f"{self.telegram_user} - {self.inspiration.date} ({self.language})"
