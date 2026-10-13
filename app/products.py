import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.schemas import Produto


@lru_cache
def load_products() -> list[Produto]:
    data = json.loads(Path(get_settings().products_file).read_text(encoding="utf-8"))
    return [Produto(**item) for item in data]


def normalize(text: str) -> str:
    # Busca sem diferenciar acentos e maiúsculas: "cafe" encontra "Café".
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))
