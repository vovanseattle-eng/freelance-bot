import hashlib
import html
import re
from bs4 import BeautifulSoup

def clean_html(raw_html: str) -> str:
    """Удаляет мусорные HTML-теги, сохраняя абзацы, переносы строк и структуру текста."""
    if not raw_html:
        return ""
    
    # Декодируем сущности (&amp;, &quot;, &#8381; и т.д.)
    unescaped = html.unescape(raw_html)
    
    # Заменяем блочные разделители на перенос строки
    formatted = re.sub(r"<(?:br|p|div|li)[^>]*>", "\n", unescaped, flags=re.IGNORECASE)
    # Удаляем остальные теги
    clean_text = re.sub(r"<[^>]+>", "", formatted)
    
    # Нормализуем пробелы и переводы строк
    lines = [line.strip() for line in clean_text.split("\n")]
    result_lines = []
    prev_empty = False
    for line in lines:
        if line:
            result_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            result_lines.append("")
            prev_empty = True
            
    return "\n".join(result_lines).strip()

def safe_truncate_html(html_str: str, max_len: int = 650) -> str:
    """Обрезает HTML-текст без разрыва тегов (автоматически закрывает открытые <a>, <b>)."""
    if not html_str:
        return ""
    if len(html_str) <= max_len:
        return html_str
    
    # Режем по последнему пробелу перед лимитом
    sliced = html_str[:max_len]
    if " " in sliced:
        sliced = sliced.rsplit(" ", 1)[0]
    sliced += "..."
    
    # BeautifulSoup автоматически валидирует и закрывает все открытые теги
    soup = BeautifulSoup(sliced, "html.parser")
    return soup.decode_contents().strip()

def generate_hash(title: str, text: str) -> str:
    """Генерирует стабильный MD5-хеш для дедупликации заказов."""
    normalized_title = "".join(re.findall(r"[a-zа-яё0-9]", title.lower()))
    normalized_body = "".join(re.findall(r"[a-zа-яё0-9]", text[:150].lower()))
    combined = f"{normalized_title}::{normalized_body}"
    return hashlib.md5(combined.encode("utf-8")).hexdigest()
