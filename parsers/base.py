from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedOrder:
    source: str
    title: str
    link: str
    description: str
    budget: str
    category: str
    content_hash: str
    contact: Optional[str] = None
    external_id: Optional[str] = None
