import hashlib
import html
import re

def clean_html(raw_html: str) -> str:
    """Удаляет HTML-теги, декодирует сущности (&amp;, &#8381;) и лишние пробелы."""
    unescaped = html.unescape(raw_html)
    cleanr = re.compile(r"<.*?>")
    text = re.sub(cleanr, "", unescaped)
    return " ".join(text.split())


def generate_hash(title: str, text: str) -> str:
    """Генерирует стабильный MD5-хеш для дедупликации заказов."""
    normalized_title = "".join(re.findall(r"[a-zа-яё0-9]", title.lower()))
    normalized_body = "".join(re.findall(r"[a-zа-яё0-9]", text[:150].lower()))
    combined = f"{normalized_title}::{normalized_body}"
    return hashlib.md5(combined.encode("utf-8")).hexdigest()
