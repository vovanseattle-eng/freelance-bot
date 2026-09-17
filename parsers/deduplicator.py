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


from collections import deque


class SeenOrdersCache:
    """
    Легковесный in-memory FIFO-кэш хэшей заказов фиксированного размера.
    Хранит не более max_size хэшей в оперативной памяти (~150 КБ RAM),
    предотвращая утечки памяти и повторную отправку уведомлений.
    """
    def __init__(self, max_size: int = 2000):
        self.max_size = max_size
        self._deque = deque()
        self._set = set()

    def is_new(self, content_hash: str) -> bool:
        if not content_hash or content_hash in self._set:
            return False
        if len(self._deque) >= self.max_size:
            oldest = self._deque.popleft()
            self._set.discard(oldest)
        self._deque.append(content_hash)
        self._set.add(content_hash)
        return True

    def __contains__(self, content_hash: str) -> bool:
        return content_hash in self._set

    def __len__(self) -> int:
        return len(self._set)

