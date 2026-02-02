# Generated migration for multi-book selection feature

from django.db import migrations, models


def migrate_selected_books(apps, schema_editor):
    """Migrate existing selected_book to selected_books ManyToMany field."""
    UserSettings = apps.get_model('core', 'UserSettings')
    
    for settings in UserSettings.objects.all():
        if settings.selected_book:
            settings.selected_books.add(settings.selected_book)


def reverse_migrate_selected_books(apps, schema_editor):
    """Reverse migration - clear selected_books."""
    UserSettings = apps.get_model('core', 'UserSettings')
    
    for settings in UserSettings.objects.all():
        settings.selected_books.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_timezone_to_usersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='selected_books',
            field=models.ManyToManyField(
                blank=True,
                related_name='user_settings_multi',
                to='core.book',
                verbose_name='Selected books'
            ),
        ),
        migrations.RunPython(migrate_selected_books, reverse_migrate_selected_books),
    ]

