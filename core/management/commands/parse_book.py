"""
Management command for parsing books from egwwritings.org.
"""
from django.core.management.base import BaseCommand, CommandError

from core.models import Book
from core.parsers import EGWBookParser


class Command(BaseCommand):
    help = "Parse book from egwwritings.org, starting from first page URL (January 1)"

    def add_arguments(self, parser):
        parser.add_argument(
            "book_id",
            type=int,
            help="Book ID from database"
        )
        parser.add_argument(
            "--start-url",
            type=str,
            help="URL of first page (January 1). If not specified, uses book source_url"
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay between requests in seconds (default: 1.0)"
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=400,
            help="Maximum number of pages to parse (default: 400)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reparse book even if already parsed"
        )
        parser.add_argument(
            "--use-selenium",
            action="store_true",
            help="Use Selenium for parsing (for JavaScript sites)"
        )

    def handle(self, *args, **options):
        book_id = options["book_id"]
        start_url = options.get("start_url")
        delay = options.get("delay", 1.0)
        max_pages = options.get("max_pages", 400)
        force = options.get("force", False)
        use_selenium = options.get("use_selenium", False)

        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            raise CommandError(f"Book with ID {book_id} not found")

        if book.is_parsed and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Book "{book.title}" already parsed. '
                    f"Use --force to reparse."
                )
            )
            return

        if not start_url:
            start_url = book.source_url
            if not start_url:
                raise CommandError(
                    "Start URL not specified and book has no source_url. "
                    "Specify --start-url or add source_url to book."
                )

        self.stdout.write(f"Starting to parse book: {book.title}")
        self.stdout.write(f"Start URL: {start_url}")
        self.stdout.write(f"Delay between requests: {delay} sec")
        self.stdout.write(f"Max pages: {max_pages}")
        self.stdout.write(f"Using Selenium: {use_selenium}")

        # Створюємо функцію для логування помилок
        def log_error(msg: str):
            self.stdout.write(self.style.ERROR(f"ERROR: {msg}"))

        parser = EGWBookParser(
            book=book, 
            start_url=start_url, 
            delay=delay, 
            use_selenium=use_selenium,
            error_logger=log_error
        )

        try:
            stats = parser.parse_book(max_pages=max_pages)
            
            self.stdout.write(self.style.SUCCESS("\nParsing completed!"))
            self.stdout.write(f"Total pages processed: {stats['total_pages']}")
            self.stdout.write(f"Created/updated inspirations: {stats['parsed']}")
            self.stdout.write(f"Skipped: {stats['skipped']}")
            self.stdout.write(f"Errors: {stats['errors']}")
            
            # Виводимо деталі помилок, якщо вони є
            if stats.get('error_details'):
                self.stdout.write(self.style.WARNING("\nError details:"))
                for i, error_detail in enumerate(stats['error_details'], 1):
                    self.stdout.write(f"  {i}. {error_detail}")
            
        except Exception as e:
            import traceback
            error_msg = f"Error during parsing: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}"
            self.stdout.write(self.style.ERROR(error_msg))
            raise CommandError(f"Error during parsing: {e}")
