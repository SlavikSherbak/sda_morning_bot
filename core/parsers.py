"""
Parser for extracting morning readings from egwwritings.org.
"""
import logging
import re
import time
import traceback
from datetime import datetime, date
from typing import Optional, Tuple, Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from core.models import Book, DailyInspiration

logger = logging.getLogger(__name__)

# Спробуємо імпортувати selenium, якщо він доступний
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class EGWBookParser:
    """Parser for books from egwwritings.org."""
    
    def __init__(self, book: Book, start_url: str, delay: float = 1.0, use_selenium: bool = False, 
                 error_logger: Optional[Callable[[str], None]] = None):
        """
        Initialize parser.
        
        Args:
            book: Book object from database
            start_url: URL of first page (January 1)
            delay: Delay between requests in seconds
            use_selenium: Use Selenium for parsing (for JavaScript sites)
            error_logger: Optional callback function for logging errors (takes error message string)
        """
        self.book = book
        self.start_url = start_url
        self.delay = delay
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.error_logger = error_logger or (lambda msg: logger.error(msg))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.parsed_dates = set()  # Для відстеження вже розпарсених дат
        self.driver = None
        
        if self.use_selenium:
            self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium is not available. Install selenium and webdriver-manager.")
        
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            self.use_selenium = False
    
    def __del__(self):
        """Close driver on object deletion."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        
    def parse_page(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse single page and return HTML content, date and next page URL.
        
        Returns:
            Tuple[html_content, date_str, next_url]
        """
        try:
            if self.use_selenium and self.driver:
                # Використовуємо Selenium для отримання сторінки
                try:
                    self.driver.get(url)
                    # Чекаємо завантаження контенту
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        time.sleep(1)
                    except TimeoutException as e:
                        self.error_logger(f"Timeout waiting for page to load: {url} - {str(e)}")
                        return None, None, None
                    
                    html_content_raw = self.driver.page_source
                except WebDriverException as e:
                    self.error_logger(f"Selenium WebDriver error for URL {url}: {type(e).__name__} - {str(e)}")
                    return None, None, None
                except Exception as e:
                    self.error_logger(f"Selenium error for URL {url}: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}")
                    return None, None, None
            else:
                # Використовуємо requests
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    response.encoding = 'utf-8'
                    html_content_raw = response.text
                except requests.exceptions.Timeout as e:
                    self.error_logger(f"Request timeout for URL {url}: {str(e)}")
                    return None, None, None
                except requests.exceptions.HTTPError as e:
                    self.error_logger(f"HTTP error for URL {url}: Status {response.status_code} - {str(e)}")
                    return None, None, None
                except requests.exceptions.RequestException as e:
                    self.error_logger(f"Request error for URL {url}: {type(e).__name__} - {str(e)}")
                    return None, None, None
            
            try:
                soup = BeautifulSoup(html_content_raw, 'html.parser')
            except Exception as e:
                self.error_logger(f"Error parsing HTML for URL {url}: {type(e).__name__} - {str(e)}")
                return None, None, None
            
            # Знаходимо основний контент сторінки
            # Для egwwritings.org контент може бути в різних місцях
            content_div = (
                soup.find('div', class_='content') or
                soup.find('div', id='content') or
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_='book-content') or
                soup.find('div', class_='book-text') or
                soup.find('div', class_='text-content')
            )
            
            if not content_div:
                # Якщо не знайдено спеціальний контейнер, беремо body без header/footer
                content_div = soup.find('body')
                if content_div:
                    # Видаляємо header, footer, navigation, скрипти та стилі
                    for tag in content_div.find_all(['header', 'footer', 'nav', 'script', 'style']):
                        tag.decompose()
            
            if not content_div:
                self.error_logger(f"Could not find content container on page: {url}")
                self.error_logger(f"Available tags in soup: {[tag.name for tag in soup.find_all(True)[:20]]}")
                return None, None, None
            
            # Створюємо копію для збереження HTML
            try:
                content_copy = BeautifulSoup(str(content_div), 'html.parser')
            except Exception as e:
                self.error_logger(f"Error creating content copy for URL {url}: {type(e).__name__} - {str(e)}")
                return None, None, None
            
            # Знаходимо дату з контенту
            date_str = self._extract_date(content_div, url)
            
            # Знаходимо посилання на наступну сторінку (до видалення навігації)
            next_url = self._find_next_link(soup, url)
            
            # Отримуємо HTML контент з форматуванням
            html_content = str(content_copy)
            
            return html_content, date_str, next_url
            
        except Exception as e:
            self.error_logger(f"Unexpected error parsing page {url}: {type(e).__name__} - {str(e)}\n{traceback.format_exc()}")
            return None, None, None
    
    def _extract_date(self, content: BeautifulSoup, url: str) -> Optional[str]:
        """
        Extract date from page content.
        
        Searches for date in formats "1 січня", "1 января", "January 1", etc.
        """
        # Спочатку шукаємо в заголовках (h1, h2, h3)
        headers = content.find_all(['h1', 'h2', 'h3', 'h4'])
        text_to_search = []
        for header in headers:
            header_text = header.get_text()
            text_to_search.append(header_text)
        
        # Також шукаємо в першому параграфі або перших 500 символах
        first_p = content.find('p')
        if first_p:
            text_to_search.append(first_p.get_text())
        
        # Додаємо весь текст якщо не знайдено в заголовках
        if not text_to_search:
            text_to_search = [content.get_text()]
        
        # Об'єднуємо весь текст для пошуку
        text = ' '.join(text_to_search)
        
        # Патерни для різних форматів дат
        patterns = [
            # Українська: "1 січня", "1 січня.", "1 січня 2024", "1 січня. Джерело"
            r'(\d{1,2})\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)',
            # Російська: "1 января", "1 января."
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)',
            # Англійська: "January 1", "Jan 1"
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})',
        ]
        
        month_names_uk = {
            'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
            'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
            'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
        }
        
        month_names_ru = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        month_names_en = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        current_year = datetime.now().year
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:
                    if groups[0].isdigit():
                        # Формат: "1 січня" або "1 января"
                        day = int(groups[0])
                        month_name = groups[1].lower()
                        
                        if month_name in month_names_uk:
                            month = month_names_uk[month_name]
                        elif month_name in month_names_ru:
                            month = month_names_ru[month_name]
                        else:
                            continue
                    else:
                        # Формат: "January 1"
                        month_name = groups[0].lower()
                        day = int(groups[1])
                        
                        if month_name in month_names_en:
                            month = month_names_en[month_name]
                        else:
                            continue
                    
                    try:
                        parsed_date = date(current_year, month, day)
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
        
        # Якщо не знайдено дату в тексті, спробуємо витягнути з URL
        # URL може містити дату в форматі #22 (номер розділу)
        # Але для визначення дати з номера розділу потрібно знати структуру книги
        return None
    
    def _find_next_link(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Find link to next page.
        
        Searches for "Next" button or similar link.
        """
        # Шукаємо посилання з текстом "Next", "Наступна", "Следующая" тощо
        next_texts = ['next', 'наступна', 'следующая', 'далі', 'далее', '→', '>', 'наступний', 'следующий']
        
        # Спочатку шукаємо точний текст
        for text in next_texts:
            # Шукаємо посилання з таким текстом (точний збіг або частина)
            links = soup.find_all('a', string=re.compile(f'^{re.escape(text)}$', re.IGNORECASE))
            for link in links:
                if link.get('href'):
                    next_url = urljoin(current_url, link['href'])
                    # Перевіряємо, що це не поточне посилання
                    if next_url != current_url:
                        return next_url
            
            # Шукаємо посилання, що містить текст
            links = soup.find_all('a', string=re.compile(text, re.IGNORECASE))
            for link in links:
                if link.get('href'):
                    next_url = urljoin(current_url, link['href'])
                    if next_url != current_url:
                        return next_url
            
            # Шукаємо посилання з title або aria-label
            link = soup.find('a', {'title': re.compile(text, re.IGNORECASE)})
            if link and link.get('href'):
                next_url = urljoin(current_url, link['href'])
                if next_url != current_url:
                    return next_url
            
            link = soup.find('a', {'aria-label': re.compile(text, re.IGNORECASE)})
            if link and link.get('href'):
                next_url = urljoin(current_url, link['href'])
                if next_url != current_url:
                    return next_url
        
        # Шукаємо посилання з класом "next" або подібним
        next_classes = ['next', 'next-page', 'next-link', 'pagination-next', 'btn-next']
        for class_name in next_classes:
            # Може бути список класів
            link = soup.find('a', class_=re.compile(class_name, re.IGNORECASE))
            if link and link.get('href'):
                next_url = urljoin(current_url, link['href'])
                if next_url != current_url:
                    return next_url
        
        # Шукаємо в навігації
        nav = soup.find('nav') or soup.find('div', class_='pagination') or soup.find('div', class_='navigation')
        if nav:
            links = nav.find_all('a')
            for link in links:
                href = link.get('href')
                if href:
                    link_text = link.get_text().lower().strip()
                    if any(text in link_text for text in next_texts):
                        next_url = urljoin(current_url, href)
                        if next_url != current_url:
                            return next_url
        
        # Шукаємо всі посилання і шукаємо такі, що містять номер сторінки більший за поточний
        # Або просто шукаємо посилання з номером розділу більшим за поточний
        try:
            # Спробуємо витягнути номер з поточного URL (наприклад, #22)
            current_match = re.search(r'#(\d+)$', current_url)
            if current_match:
                current_num = int(current_match.group(1))
                # Шукаємо посилання з номером більшим за поточний
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href')
                    match = re.search(r'#(\d+)$', href)
                    if match:
                        link_num = int(match.group(1))
                        if link_num == current_num + 1:
                            next_url = urljoin(current_url, href)
                            return next_url
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def parse_book(self, max_pages: int = 400) -> dict:
        """
        Parse entire book starting from start_url.
        
        Args:
            max_pages: Maximum number of pages to parse (protection against loops)
        
        Returns:
            Dictionary with parsing statistics
        """
        stats = {
            'parsed': 0,
            'skipped': 0,
            'errors': 0,
            'total_pages': 0,
            'error_details': []  # Список деталей помилок
        }
        
        current_url = self.start_url
        pages_parsed = 0
        
        while current_url and pages_parsed < max_pages:
            html_content, date_str, next_url = self.parse_page(current_url)
            
            if not html_content:
                error_msg = f"Failed to parse page: {current_url} (no content returned)"
                stats["errors"] += 1
                stats["error_details"].append(error_msg)
                self.error_logger(error_msg)
                break
            
            stats["total_pages"] += 1
            
            if date_str:
                try:
                    inspiration_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    if inspiration_date in self.parsed_dates:
                        stats["skipped"] += 1
                    else:
                        try:
                            DailyInspiration.objects.update_or_create(
                                book=self.book,
                                date=inspiration_date,
                                defaults={
                                    "html_content": html_content,
                                    "source_url": current_url,
                                    "original_text": self._extract_text_from_html(html_content),
                                }
                            )
                            
                            stats["parsed"] += 1
                            self.parsed_dates.add(inspiration_date)
                            
                            if inspiration_date.month == 12 and inspiration_date.day == 31:
                                break
                        except Exception as e:
                            error_msg = f"Database error saving inspiration for date {date_str} from URL {current_url}: {type(e).__name__} - {str(e)}"
                            stats["errors"] += 1
                            stats["error_details"].append(error_msg)
                            self.error_logger(error_msg)
                            self.error_logger(traceback.format_exc())
                        
                except ValueError as e:
                    error_msg = f"Invalid date format '{date_str}' from URL {current_url}: {str(e)}"
                    stats["errors"] += 1
                    stats["error_details"].append(error_msg)
                    self.error_logger(error_msg)
            else:
                # Якщо дата не знайдена, це не критична помилка, але варто залогувати
                self.error_logger(f"Warning: Could not extract date from URL {current_url}")
            
            if next_url:
                current_url = next_url
            else:
                self.error_logger(f"No next URL found after parsing: {current_url}")
                break
            
            pages_parsed += 1
            
            # Затримка між запитами
            if self.delay > 0:
                time.sleep(self.delay)
        
        # Оновлюємо статус книги
        try:
            self.book.is_parsed = True
            self.book.last_parsed_at = timezone.now()
            self.book.save()
        except Exception as e:
            error_msg = f"Error updating book status: {type(e).__name__} - {str(e)}"
            stats["error_details"].append(error_msg)
            self.error_logger(error_msg)
        
        return stats
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        soup = BeautifulSoup(html_content, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        return soup.get_text(separator="\n", strip=True)
