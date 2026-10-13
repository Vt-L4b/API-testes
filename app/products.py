import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.schemas import EstoqueLoja, Loja, Produto, ProdutoResposta


def _read_json(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache
def load_products() -> list[Produto]:
    return [Produto(**item) for item in _read_json(get_settings().products_file)]


@lru_cache
def load_stores() -> list[Loja]:
    return [Loja(**item) for item in _read_json(get_settings().stores_file)]


def normalize(text: str) -> str:
    # Busca sem diferenciar acentos e maiúsculas: "cafe" encontra "Café".
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def find_store(keyword: str) -> Loja | None:
    # Aceita o Id ("2168") ou o nome ("Loja 2168", "loja 2168"). Compara palavras inteiras,
    # para que um código incompleto ("21") não caia na loja errada.
    termos = [t for t in normalize(keyword).split() if t != "loja"]
    if not termos:
        return None
    for store in load_stores():
        nome = normalize(store.Name).split()
        if " ".join(termos) == normalize(store.Id) or all(t in nome for t in termos):
            return store
    return None


def with_availability(product: Produto, store: Loja | None) -> ProdutoResposta:
    stores = [store] if store else load_stores()
    stock = [
        EstoqueLoja(
            StoreId=s.Id,
            StoreName=s.Name,
            Quantity=product.Stock.get(s.Id, 0),
            Availability="available" if product.Stock.get(s.Id, 0) > 0 else "unavailable",
        )
        for s in stores
    ]
    available = any(s.Quantity > 0 for s in stock)
    return ProdutoResposta(
        **product.model_dump(),
        Stock=product.Stock,
        Availability="available" if available else "unavailable",
        Stores=stock,
    )
