# ASD Morning Bot

A Django-based Telegram bot that sends daily morning inspirations from books to users at scheduled times.

## Features

- **Daily Inspirations**: Automatically sends daily inspirations from selected books at scheduled times
- **Full Multi-language Support**: Complete interface translation in Ukrainian, English, and Russian
- **Language Selection**: Users choose their preferred language at first start
- **Precise Scheduling**: Users configure exact notification time (no time window needed)
- **Book Selection by Language**: First select book language, then choose from available books
- **Random Day**: Access random inspirations from selected books
- **Template System**: All bot messages stored in HTML templates for easy editing
- **Celery Integration**: Uses Celery for scheduled task execution
- **Enhanced Admin Panel**: Django Grappelli for improved admin interface

## Technology Stack

- **Django 5.0+**: Web framework
- **django-grappelli**: Enhanced admin interface
- **aiogram 3.0+**: Telegram bot framework
- **Celery**: Distributed task queue
- **Redis**: Message broker and result backend
- **BeautifulSoup4**: HTML parsing
- **PostgreSQL/SQLite**: Database

## Installation

### Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.10+, Redis server, PostgreSQL or SQLite (for local development)

### Setup with Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd asd_morning_bot
```

2. Create `.env` file from `env.example`:
```bash
cp env.example .env
```

3. Configure environment variables in `.env`:
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_ENGINE=postgresql
DATABASE_NAME=asd_morning_bot
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=postgres
DATABASE_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
EGW_API_AUTH_TOKEN=your-api-token
```

4. Build and start all services:
```bash
./dc.sh up -d --build
```

5. Run migrations:
```bash
./manage.sh migrate
```

6. Collect static files (including Grappelli):
```bash
./manage.sh collectstatic
```

7. Create superuser:
```bash
./manage.sh createsuperuser
```

### Setup without Docker (Local Development)

1. Clone the repository:
```bash
git clone <repository-url>
cd asd_morning_bot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install optional parser dependencies (if needed):
```bash
pip install selenium webdriver-manager
```

5. Create `.env` file from `env.example`:
```bash
cp env.example .env
```

6. Configure environment variables in `.env` (use localhost for Redis and SQLite):
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EGW_API_AUTH_TOKEN=your-api-token
```

7. Run migrations:
```bash
python manage.py migrate
```

8. Collect static files (including Grappelli):
```bash
python manage.py collectstatic
```

9. Create superuser:
```bash
python manage.py createsuperuser
```

## Usage

### Running with Docker

All services run automatically when you start Docker Compose:

```bash
# Start all services (Django app, Celery worker, Celery beat, Bot, PostgreSQL, Redis)
./dc.sh up -d

# View logs
./dc.sh logs -f

# View logs for specific service
./dc.sh logs -f app
./dc.sh logs -f bot
./dc.sh logs -f celery-worker
./dc.sh logs -f celery-beat

# Stop all services
./dc.sh down

# Stop and remove volumes (⚠️ deletes database data)
./dc.sh down -v
```

### Running without Docker (Local Development)

1. Start Redis server:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A config worker -l info
```

3. Start Celery beat (scheduler):
```bash
celery -A config beat -l info
```

4. Start the bot:
```bash
python manage.py run_bot
```

Or use the provided script:
```bash
./run.sh
```

### Docker Management Commands

```bash
# Run Django management commands
./manage.sh migrate
./manage.sh createsuperuser
./manage.sh shell
./manage.sh collectstatic

# Execute command in container
./dc.sh exec app bash
./dc.sh exec celery-worker bash

# Rebuild containers after code changes
./dc.sh up -d --build
```

### Parsing Books

To parse a book from egwwritings.org:

```bash
python manage.py parse_book <book_id> --start-url <url> [options]
```

Options:
- `--start-url`: URL of first page (January 1). If not specified, uses book `source_url`
- `--delay`: Delay between requests in seconds (default: 1.0)
- `--max-pages`: Maximum number of pages to parse (default: 400)
- `--force`: Reparse book even if already parsed
- `--use-selenium`: Use Selenium for parsing (for JavaScript sites)

Example:
```bash
python manage.py parse_book 1 --start-url "https://example.com/book/1" --delay 1.5
```

### Admin Interface

Access Django admin at `http://localhost:8000/admin/` (with Grappelli enhanced interface) to:
- Manage books (add, edit, activate/deactivate)
- Manage daily inspirations (view, edit translations)
- View and manage user settings
- Monitor sent inspirations
- Configure Celery Beat schedules

The admin interface uses **django-grappelli** for improved usability and modern design.

## Project Structure

```
asd_morning_bot/
├── bot/                    # Telegram bot application
│   ├── handlers/          # Message handlers
│   │   ├── start.py      # Start command and language selection
│   │   ├── settings.py   # Settings handlers
│   │   └── messages.py   # Message handlers
│   ├── templates/         # Message templates
│   │   └── messages/     # HTML templates for bot messages
│   │       ├── uk/       # Ukrainian templates
│   │       ├── ru/       # Russian templates
│   │       └── en/       # English templates
│   ├── keyboards.py       # Keyboard layouts
│   ├── tasks.py           # Celery tasks
│   ├── utils.py           # Utility functions
│   └── bot.py             # Bot initialization
├── core/                   # Core application
│   ├── models.py          # Database models
│   ├── parsers.py         # Book parsing logic
│   ├── admin.py           # Django admin configuration
│   └── constants.py       # Constants (languages, etc.)
├── config/                 # Django configuration
│   ├── settings.py        # Settings
│   ├── celery.py          # Celery configuration
│   └── urls.py            # URL routing
├── docker/                 # Docker configuration
│   ├── Dockerfile         # Production Dockerfile
│   ├── config/            # Configuration files
│   │   └── gunicorn.conf.py
│   └── scripts/           # Startup scripts
│       ├── server.sh      # Django app startup
│       ├── celery-worker.sh
│       ├── celery-beat.sh
│       └── bot.sh
├── docker-compose.yml      # Docker Compose configuration
├── dc.sh                   # Docker Compose helper script
├── manage.sh               # Django management helper
└── manage.py              # Django management script
```

## Docker Services

The project includes 6 Docker containers:

1. **app** - Django application server (Gunicorn)
2. **celery-worker** - Celery worker for background tasks
3. **celery-beat** - Celery beat scheduler
4. **bot** - Telegram bot service
5. **postgres** - PostgreSQL database
6. **redis** - Redis cache and message broker

## Models

- **Book**: Stores book information (title, language, source URL)
- **DailyInspiration**: Daily inspirations from books with translations
- **TelegramUser**: Telegram user information
- **UserSettings**: User preferences (notification time, selected book, language)
- **SentInspiration**: Tracking of sent inspirations to prevent duplicates

## Celery Tasks

- `send_inspirations_to_users`: Runs every 5 minutes, checks users whose notification time falls within the current 5-minute window and sends inspirations
- `fetch_daily_inspirations`: Runs daily at 00:00 UTC to fetch new inspirations (stub for future n8n integration)
- `send_inspiration_to_user`: Sends inspiration to specific user using language-specific templates

## Bot Features

### Language Support
- **Ukrainian (uk)**: Повна підтримка української мови
- **Russian (ru)**: Полная поддержка русского языка  
- **English (en)**: Full English language support

The bot interface automatically adapts to the user's selected language. All buttons, messages, and responses are displayed in the chosen language.

### User Flow
1. User starts bot with `/start` command
2. If first time, user selects interface language (Ukrainian, Russian, or English)
3. User configures notification time (exact time, e.g., 21:02)
4. User selects book language, then chooses a book from available books in that language
5. Daily inspirations are sent at the configured time within the 5-minute window

### Message Templates System
All bot messages are stored in HTML templates located in `bot/templates/messages/{language}/`:
- **Easy editing**: All text content in one place per language
- **HTML formatting**: Supports Telegram HTML tags (`<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`)
- **Variable substitution**: Use `{variable}` syntax for dynamic content
- **Centralized management**: Change messages without touching code

Template files:
- `start.html` - Welcome message
- `help.html` - Help text
- `settings.html` - Settings display
- `select_book.html` - Book selection
- `inspiration_message.html` - Daily inspiration format
- And many more...

### Notification System
- Task `send_inspirations_to_users` runs every 5 minutes
- Checks all users whose notification time falls within the current 5-minute window
- Example: At 21:05, checks users with notification time between 21:00-21:05
- Sends inspiration only once per day per user
- Uses user's selected language for message formatting

## Development

### Code Style

The project follows PEP 8 and uses:
- **Ruff**: Linting and formatting
- **Black**: Code formatting (optional)

Run linting:
```bash
ruff check .
```

### Type Annotations

All code should include type annotations for better code quality and IDE support.

### Message Templates

To edit bot messages:
1. Navigate to `bot/templates/messages/{language}/`
2. Edit the corresponding HTML template file
3. Templates support Python string formatting with `{variable}` syntax
4. Use HTML tags supported by Telegram: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`

Example template (`bot/templates/messages/uk/start.html`):
```html
👋 Вітаю, {name}!

{registration_message}

📱 Використовуйте кнопки меню для навігації.
```

## Troubleshooting

### Docker Issues

**Problem**: Containers fail to start
- Check if `.env` file exists and is properly configured
- Verify Docker and Docker Compose are installed and running
- Check logs: `./dc.sh logs`

**Problem**: Database connection errors
- Ensure PostgreSQL container is healthy: `./dc.sh ps`
- Check database credentials in `.env`
- Wait for PostgreSQL to be ready (healthcheck may take a few seconds)

**Problem**: Redis connection errors
- Ensure Redis container is running: `./dc.sh ps`
- Check Redis configuration in `.env`

**Problem**: Bot not receiving messages
- Verify `TELEGRAM_BOT_TOKEN` is set correctly in `.env`
- Check bot logs: `./dc.sh logs -f bot`
- Ensure bot container is running: `./dc.sh ps`

**Problem**: Admin panel styles not loading
- Run `collectstatic`: `./manage.sh collectstatic`
- Ensure `grappelli` is in `INSTALLED_APPS` before `django.contrib.admin`
- Check static files are served correctly in production

### Local Development Issues

**Problem**: Celery tasks not executing
- Ensure Redis is running: `redis-cli ping`
- Check Celery worker logs
- Verify `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in `.env`
- Ensure Celery Beat is running for scheduled tasks

**Problem**: Inspirations not sent at configured time
- Task runs every 5 minutes and checks users whose notification time falls within the current 5-minute window
- Example: If task runs at 21:05, it checks users with notification time between 21:00-21:05
- Verify user's notification time is set correctly
- Check that user has selected a book
- Ensure Celery Beat is running

## Deployment

### Quick Start

For a quick deployment guide, see [DEPLOYMENT_QUICKSTART.md](./DEPLOYMENT_QUICKSTART.md).

### Full Deployment Guide

For detailed deployment instructions including:
- Hosting provider recommendations (Hetzner, DigitalOcean, Vultr, etc.)
- Server setup and configuration
- Nginx reverse proxy setup
- SSL certificate configuration (Let's Encrypt)
- Production environment variables
- Backup and monitoring setup
- Troubleshooting

See [DEPLOYMENT.md](./DEPLOYMENT.md).

### Recommended Hosting Providers

- **Hetzner Cloud**: €4.15/month (recommended) - https://www.hetzner.com/cloud
- **DigitalOcean**: $4/month - https://www.digitalocean.com
- **Vultr**: $2.50/month - https://www.vultr.com
- **Linode**: $5/month - https://www.linode.com

All providers include static IP addresses by default.

### Minimum Server Requirements

- **CPU**: 1-2 vCPU
- **RAM**: 1-2GB (2GB+ recommended)
- **Storage**: 20GB+ SSD
- **OS**: Ubuntu 22.04 LTS or Debian 12
- **Static IP**: Included by default with most providers

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
