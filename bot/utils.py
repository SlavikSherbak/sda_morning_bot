import re
from bs4 import BeautifulSoup
from asgiref.sync import sync_to_async
import pytz
from timezonefinder import TimezoneFinder
from core.models import TelegramUser, UserSettings
from bot.templates.translations import get_text, t

_timezone_finder = TimezoneFinder(in_memory=True)


def detect_timezone_from_location(latitude: float, longitude: float) -> pytz.BaseTzInfo:
    """
    Визначає часову зону на основі координат локації користувача.
    Повертає pytz timezone об'єкт.
    """
    try:
        timezone_str = _timezone_finder.timezone_at(lng=longitude, lat=latitude)
        if timezone_str:
            return pytz.timezone(timezone_str)
    except Exception:
        pass
    
    return pytz.timezone("Europe/Kyiv")


def detect_timezone_from_language_code(language_code: str) -> pytz.BaseTzInfo:
    """
    Автоматично визначає часову зону на основі language_code користувача.
    Використовується як fallback, коли локація недоступна.
    Повертає pytz timezone об'єкт.
    """
    if not language_code:
        return pytz.timezone("Europe/Kyiv")
    
    language_code = language_code.lower()
    
    timezone_mapping = {
        "uk": "Europe/Kyiv",
        "ru": "Europe/Moscow",
        "en": "Europe/London",
        "en-us": "America/New_York",
        "en-gb": "Europe/London",
        "en-ie": "Europe/Dublin",
        "pl": "Europe/Warsaw",
        "de": "Europe/Berlin",
        "fr": "Europe/Paris",
        "es": "Europe/Madrid",
        "it": "Europe/Rome",
        "pt": "Europe/Lisbon",
        "ro": "Europe/Bucharest",
        "tr": "Europe/Istanbul",
        "ar": "Asia/Dubai",
        "zh": "Asia/Shanghai",
        "ja": "Asia/Tokyo",
        "ko": "Asia/Seoul",
        "hi": "Asia/Kolkata",
    }
    
    timezone_str = timezone_mapping.get(language_code, "Europe/Kyiv")
    
    if language_code.startswith("en-"):
        if "us" in language_code or "ca" in language_code:
            timezone_str = "America/New_York"
        elif "ie" in language_code:
            timezone_str = "Europe/Dublin"
        elif "gb" in language_code or "uk" in language_code:
            timezone_str = "Europe/London"
        elif "au" in language_code:
            timezone_str = "Australia/Sydney"
    
    return pytz.timezone(timezone_str)


def convert_html_to_telegram(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    
    for tag in soup.find_all("span", class_=lambda x: x and "page-break" in str(x).lower()):
        tag.decompose()
    
    for tag in soup.find_all(
        ["span", "div"],
        class_=lambda x: x
        and (
            "refcode" in str(x).lower()
            or "pager" in str(x).lower()
            or "breadcrumb" in str(x).lower()
        ),
    ):
        tag.decompose()
    
    content_headers = soup.find_all(
        ["h3", "h1"], class_=lambda x: x and "egw_content" in str(x)
    )
    content_spans = soup.find_all("span", class_="egw_content")
    
    header_ids = set()
    for header in content_headers:
        header_spans = header.find_all("span", class_="egw_content")
        for span in header_spans:
            header_ids.add(id(span))
    
    content_spans = [span for span in content_spans if id(span) not in header_ids]
    
    main_content = soup.new_tag("div")
    
    if content_headers:
        for header in content_headers:
            header_span = header.find("span", class_="egw_content")
            if header_span:
                header_text = header_span.get_text(strip=True)
            else:
                header_text = header.get_text(strip=True)
            
            if header_text:
                bold_tag = soup.new_tag("b")
                bold_tag.string = header_text
                main_content.append(bold_tag)
                main_content.append("\n\n")
    
    if content_spans:
        for idx, span in enumerate(content_spans):
            parent_p = span.find_parent("p")
            parent_id = parent_p.get("id") if parent_p and parent_p.get("id") else None
            
            allowed_tags_in_span = ["b", "i", "u", "s", "code", "pre", "a", "strong", "em"]
            
            for tag in span.find_all("strong"):
                tag.name = "b"
                tag.attrs = {}
            
            for tag in span.find_all("em"):
                tag.name = "i"
                tag.attrs = {}
            
            for tag in span.find_all("a", href=True):
                href = tag.get("href", "")
                if href.startswith("http://") or href.startswith("https://"):
                    tag.attrs = {"href": href}
                else:
                    tag.unwrap()
            
            while True:
                found = False
                for tag in span.find_all(True):
                    if tag.name not in allowed_tags_in_span:
                        tag.unwrap()
                        found = True
                if not found:
                    break
            
            for tag in span.find_all(["b", "i", "u", "s", "code", "pre"]):
                tag.attrs = {}
            
            span_html = str(span)
            span_soup = BeautifulSoup(span_html, "html.parser")
            
            allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]
            for tag in span_soup.find_all(True):
                if tag.name not in allowed_tags:
                    tag.unwrap()
            
            for tag in span_soup.find_all(["b", "i", "u", "s", "code", "pre"]):
                tag.attrs = {}
            
            for tag in span_soup.find_all("a", href=True):
                href = tag.get("href", "")
                if href.startswith("http://") or href.startswith("https://"):
                    tag.attrs = {"href": href}
                else:
                    tag.unwrap()
            
            span_content = span_soup.decode_contents()
            if span_content.strip():
                main_content.append(span_content)
                
                if idx < len(content_spans) - 1:
                    next_span = content_spans[idx + 1]
                    next_parent_p = next_span.find_parent("p")
                    next_parent_id = (
                        next_parent_p.get("id")
                        if next_parent_p and next_parent_p.get("id")
                        else None
                    )
                    
                    if parent_p != next_parent_p or parent_id != next_parent_id:
                        main_content.append("\n\n")
                    else:
                        main_content.append(" ")
                else:
                    main_content.append("\n\n")
    
    if not content_spans and not content_headers:
        main_content = (
            soup.find("div", class_="book-content")
            or soup.find("div", class_="egw_content_container")
            or soup.find("body")
            or soup
        )
        
        for tag in main_content.find_all("strong"):
            tag.name = "b"
            tag.attrs = {}
        
        for tag in main_content.find_all("em"):
            tag.name = "i"
            tag.attrs = {}
        
        for tag in main_content.find_all("a", href=True):
            href = tag.get("href", "")
            if href.startswith("http://") or href.startswith("https://"):
                tag.attrs = {"href": href}
            else:
                tag.unwrap()
        
        for tag in main_content.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]):
            if tag.next_sibling:
                tag.insert_after("\n\n")
            if tag.previous_sibling:
                tag.insert_before("\n")
            tag.unwrap()
    
    for tag in main_content.find_all(["ul", "ol"]):
        if tag.next_sibling:
            tag.insert_after("\n")
        tag.unwrap()
    
    for tag in main_content.find_all("li"):
        if tag.contents:
            tag.insert(0, "• ")
        if tag.next_sibling:
            tag.insert_after("\n")
        tag.unwrap()
    
    for tag in main_content.find_all("br"):
        tag.replace_with("\n")
    
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]
    while True:
        found = False
        for tag in main_content.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
                found = True
        if not found:
            break
    
    for tag in main_content.find_all(["b", "i", "u", "s", "code", "pre"]):
        tag.attrs = {}
    
    if main_content.name == "div":
        result = main_content.decode_contents()
    else:
        result = str(main_content)
    
    final_soup = BeautifulSoup(result, "html.parser")
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]
    
    while True:
        found = False
        for tag in final_soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
                found = True
        if not found:
            break
    
    for tag in final_soup.find_all(["b", "i", "u", "s", "code", "pre"]):
        tag.attrs = {}
    
    for tag in final_soup.find_all("a", href=True):
        href = tag.get("href", "")
        if href.startswith("http://") or href.startswith("https://"):
            tag.attrs = {"href": href}
        else:
            tag.unwrap()
    
    if final_soup.body:
        result = final_soup.body.decode_contents()
    elif final_soup.html:
        result = final_soup.html.decode_contents()
    else:
        result = final_soup.decode_contents()
    
    final_cleanup = BeautifulSoup(result, "html.parser")
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]
    
    while True:
        found = False
        for tag in final_cleanup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
                found = True
        if not found:
            break
    
    for tag in final_cleanup.find_all(["b", "i", "u", "s", "code", "pre"]):
        tag.attrs = {}
    
    for tag in final_cleanup.find_all("a", href=True):
        href = tag.get("href", "")
        if href.startswith("http://") or href.startswith("https://"):
            tag.attrs = {"href": href}
        else:
            tag.unwrap()
    
    if final_cleanup.body:
        result = final_cleanup.body.decode_contents()
    elif final_cleanup.html:
        result = final_cleanup.html.decode_contents()
    else:
        result = final_cleanup.decode_contents()
    
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    
    parts = result.split("\n\n")
    cleaned_parts = []
    
    for part in parts:
        cleaned = re.sub(r"[ \t]+", " ", part.strip())
        if cleaned:
            cleaned_parts.append(cleaned)
    
    content = "\n\n".join(cleaned_parts)
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"<([^>]+)></\1>", "", content)
    content = re.sub(r"<(?!/?(?:b|i|u|s|code|pre|a\b))[^>]+>", "", content)
    content = re.sub(r"</(?!(?:b|i|u|s|code|pre|a\b))[^>]+>", "", content)
    
    unwanted_tags = ["span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "br", "hr"]
    for tag_name in unwanted_tags:
        content = re.sub(rf"<{tag_name}[^>]*>", "", content, flags=re.IGNORECASE)
        content = re.sub(rf"</{tag_name}>", "", content, flags=re.IGNORECASE)
    
    content = re.sub(r"<(b|i|u|s|code|pre)(\s[^>]*)?>", r"<\1>", content)
    content = re.sub(r'<a\s+([^>]*href=["\']([^"\']+)["\'][^>]*)>', r'<a href="\2">', content)
    content = re.sub(r"<a\s+[^>]*>", "", content)
    content = re.sub(r"</a>", "", content)
    
    lines = content.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
        elif cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append("")
    
    content = "\n".join(cleaned_lines)
    content = re.sub(r"\n\n+", "\n\n", content)
    
    return content.strip()


async def get_user_language(telegram_id: int) -> str:
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=telegram_id)
        try:
            settings = await sync_to_async(UserSettings.objects.get)(telegram_user=telegram_user)
            return settings.language
        except UserSettings.DoesNotExist:
            return "uk"
    except TelegramUser.DoesNotExist:
        return "uk"
