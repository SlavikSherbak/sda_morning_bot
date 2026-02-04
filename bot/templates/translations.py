"""
Translation system for bot messages.
"""
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "messages"


def load_template(language: str, template_name: str) -> str:
    """
    Load template for specific language.
    
    Args:
        language: Language code (uk, ru, en)
        template_name: Name of template file (without extension)
    
    Returns:
        Template content as string
    """
    template_path = TEMPLATES_DIR / language / f"{template_name}.html"
    
    if not template_path.exists():
        # Fallback to Ukrainian if template doesn't exist
        template_path = TEMPLATES_DIR / "uk" / f"{template_name}.html"
    
    if not template_path.exists():
        return f"[Template {template_name} not found]"
    
    return template_path.read_text(encoding="utf-8")


def get_text(language: str, key: str, **kwargs) -> str:
    """
    Get translated text by key.
    
    Args:
        language: Language code (uk, ru, en)
        key: Translation key
        **kwargs: Variables to format into template
    
    Returns:
        Formatted text
    """
    template = load_template(language, key)
    
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"[Template error: {e}]"
    
    return template


# Translation keys mapping for buttons and simple texts
TRANSLATIONS = {
    "uk": {
        "cancel": "❌ Скасувати",
        "back": "⬅️ Назад",
        "done": "💾 Зберегти",
        "main_menu": "🏠 Головне меню",
        "select_action": "Оберіть дію з меню",
        "my_settings": "📋 Мої налаштування",
        "my_profile": "👤 Мій профіль",
        "set_time": "⏰ Налаштувати час",
        "select_book": "📚 Обрати книгу",
        "select_language": "🌐 Обрати мову",
        "help": "ℹ️ Допомога",
        "random_day": "🎲 Випадковий день",
        "ukrainian": "🇺🇦 Українська",
        "english": "🇬🇧 English",
        "russian": "🇷🇺 Русский",
        "active": "🟢 Активний",
        "inactive": "🔴 Неактивний",
        "settings_created": "✅ Налаштування створені",
        "settings_not_created": "⚠️ Налаштування не створені",
        "not_specified": "Не вказано",
        "select_timezone": "🌍 Обрати часовий пояс",
        "timezone_selected": "Часовий пояс",
        "share_location": "🌍 Синхронізувати часовий пояс",
        "skip": "⏭️ Пропустити",
        "request_location": "🌍 Для точного визначення вашого часового поясу, будь ласка, надішліть вашу поточну локацію.\n\nАбо ви можете пропустити цей крок - тоді часова зона буде визначена приблизно на основі вашої мови.",
        "location_received": "✅ Часовий пояс синхронізовано: {timezone}",
        "location_skipped": "⏭️ Використано приблизний часовий пояс на основі вашої мови.",
        "no_books_selected": "⚠️ Будь ласка, оберіть хоча б одну книгу",
        "books_selected": "✅ Обрані книги:\n\n{books_list}",
    },
    "ru": {
        "cancel": "❌ Отменить",
        "back": "⬅️ Назад",
        "done": "💾 Сохранить",
        "main_menu": "🏠 Главное меню",
        "select_action": "Выберите действие из меню",
        "my_settings": "📋 Мои настройки",
        "my_profile": "👤 Мой профиль",
        "set_time": "⏰ Настроить время",
        "select_book": "📚 Выбрать книгу",
        "select_language": "🌐 Выбрать язык",
        "help": "ℹ️ Справка",
        "random_day": "🎲 Случайный день",
        "ukrainian": "🇺🇦 Українська",
        "english": "🇬🇧 English",
        "russian": "🇷🇺 Русский",
        "active": "🟢 Активный",
        "inactive": "🔴 Неактивный",
        "settings_created": "✅ Настройки созданы",
        "settings_not_created": "⚠️ Настройки не созданы",
        "not_specified": "Не указано",
        "select_timezone": "🌍 Выбрать часовой пояс",
        "timezone_selected": "Часовой пояс",
        "share_location": "🌍 Синхронизировать часовой пояс",
        "skip": "⏭️ Пропустить",
        "request_location": "🌍 Для точного определения вашего часового пояса, пожалуйста, отправьте вашу текущую локацию.\n\nИли вы можете пропустить этот шаг - тогда часовой пояс будет определен приблизительно на основе вашего языка.",
        "location_received": "✅ Часовой пояс синхронизирован: {timezone}",
        "location_skipped": "⏭️ Использован приблизительный часовой пояс на основе вашего языка.",
        "no_books_selected": "⚠️ Пожалуйста, выберите хотя бы одну книгу",
        "books_selected": "✅ Выбранные книги:\n\n{books_list}",
    },
    "en": {
        "cancel": "❌ Cancel",
        "back": "⬅️ Back",
        "done": "💾 Save",
        "main_menu": "🏠 Main menu",
        "select_action": "Select an action from the menu",
        "my_settings": "📋 My Settings",
        "my_profile": "👤 My Profile",
        "set_time": "⏰ Set Time",
        "select_book": "📚 Select Book",
        "select_language": "🌐 Select Language",
        "select_timezone": "🌍 Select Timezone",
        "help": "ℹ️ Help",
        "random_day": "🎲 Random Day",
        "ukrainian": "🇺🇦 Українська",
        "english": "🇬🇧 English",
        "russian": "🇷🇺 Русский",
        "active": "🟢 Active",
        "inactive": "🔴 Inactive",
        "settings_created": "✅ Settings created",
        "settings_not_created": "⚠️ Settings not created",
        "not_specified": "Not specified",
        "timezone_selected": "Timezone",
        "share_location": "🌍 Synchronize Timezone",
        "skip": "⏭️ Skip",
        "request_location": "🌍 To accurately determine your timezone, please share your current location.\n\nOr you can skip this step - then the timezone will be determined approximately based on your language.",
        "location_received": "✅ Timezone synchronized: {timezone}",
        "location_skipped": "⏭️ Using approximate timezone based on your language.",
        "no_books_selected": "⚠️ Please select at least one book",
        "books_selected": "✅ Selected books:\n\n{books_list}",
    },
}


def t(language: str, key: str) -> str:
    """
    Get simple translation by key.
    
    Args:
        language: Language code (uk, ru, en)
        key: Translation key
    
    Returns:
        Translated text
    """
    return TRANSLATIONS.get(language, TRANSLATIONS["uk"]).get(key, key)
