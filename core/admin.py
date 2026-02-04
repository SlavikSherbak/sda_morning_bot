from django.contrib import admin
from .models import (
    Book,
    TelegramUser,
    UserSettings,
    DailyInspiration,
    SentInspiration,
)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "inspirations_count", "is_active", "is_parsed", "last_parsed_at", "created_at")
    list_filter = ("is_active", "is_parsed", "language", "created_at")
    search_fields = ("title", "description", "source_url")
    readonly_fields = ("created_at", "updated_at", "last_parsed_at", "inspirations_count_display")
    fieldsets = (
        ("Main information", {
            "fields": ("title", "description", "source_url", "language")
        }),
        ("Status", {
            "fields": ("is_active", "is_parsed", "last_parsed_at", "inspirations_count_display")
        }),
        ("System information", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def inspirations_count(self, obj):
        """Count of inspirations for the book."""
        return obj.daily_inspirations.count()
    inspirations_count.short_description = "Inspirations"
    inspirations_count.admin_order_field = "daily_inspirations__count"
    
    def inspirations_count_display(self, obj):
        """Display count of inspirations in detail view."""
        count = obj.daily_inspirations.count()
        return f"{count} inspirations"
    inspirations_count_display.short_description = "Inspirations count"
    


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("telegram_id", "username", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ("telegram_user", "notification_time", "timezone", "get_selected_books_display", "language", "is_active")
    list_filter = ("language", "is_active", "timezone", "created_at")
    search_fields = ("telegram_user__username", "telegram_user__first_name", "telegram_user__telegram_id")
    readonly_fields = ("created_at", "updated_at", "selected_books_display")
    filter_horizontal = ("selected_books",)
    fieldsets = (
        ("User", {
            "fields": ("telegram_user", "is_active")
        }),
        ("Time settings", {
            "fields": ("notification_time", "timezone"),
        }),
        ("Content selection", {
            "fields": ("language", "selected_books", "selected_books_display", "selected_book")
        }),
        ("System information", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def get_selected_books_display(self, obj):
        """Display selected books in list view."""
        books = obj.selected_books.all()
        if books.exists():
            return ", ".join([book.title for book in books[:3]]) + ("..." if books.count() > 3 else "")
        elif obj.selected_book:
            return f"{obj.selected_book.title} (legacy)"
        return "—"
    get_selected_books_display.short_description = "Selected books"
    
    def selected_books_display(self, obj):
        """Display all selected books in detail view."""
        books = obj.selected_books.all()
        if books.exists():
            book_list = "\n".join([f"• {book.title} ({book.language})" for book in books])
            return f"{books.count()} books:\n{book_list}"
        elif obj.selected_book:
            return f"Legacy: {obj.selected_book.title} ({obj.selected_book.language})"
        return "No books selected"
    selected_books_display.short_description = "Selected books (readonly)"


@admin.register(DailyInspiration)
class DailyInspirationAdmin(admin.ModelAdmin):
    list_display = ("book", "date", "has_translations", "created_at")
    list_filter = ("date", "book", "created_at")
    search_fields = ("book__title", "original_text", "translation_ukrainian", "translation_russian")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
    
    def has_translations(self, obj):
        """Check if translations exist."""
        return bool(obj.translation_ukrainian and obj.translation_russian)
    has_translations.boolean = True
    has_translations.short_description = "Has translations"


@admin.register(SentInspiration)
class SentInspirationAdmin(admin.ModelAdmin):
    list_display = ("telegram_user", "inspiration", "language", "sent_at")
    list_filter = ("language", "sent_at", "inspiration__date")
    search_fields = ("telegram_user__username", "telegram_user__first_name", "inspiration__book__title")
    readonly_fields = ("sent_at",)
    date_hierarchy = "sent_at"


