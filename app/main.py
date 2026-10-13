from contextlib import asynccontextmanager

from urllib.parse import parse_qsl, urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.database import Base, engine
from app.products import load_products, load_stores
from app.routers import admin, produtos


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    # Falha já na inicialização se algum JSON estiver inválido.
    load_products()
    store_ids = {s.Id for s in load_stores()}
    for p in load_products():
        unknown = set(p.Stock) - store_ids
        if unknown:
            raise ValueError(f"Produto {p.Id} tem estoque em loja inexistente: {unknown}")
    yield


app = FastAPI(title="API de produtos para testes da Whizz", lifespan=lifespan)


@app.middleware("http")
async def lowercase_query_keys(request: Request, call_next):
    # Plataformas de IA às vezes enviam "Busca" ou "Loja": tratamos os nomes sem diferenciar
    # maiúsculas. O nome original fica guardado para listar parâmetros ignorados.
    query = request.scope["query_string"].decode("latin-1")
    if query:
        request.scope["original_query_keys"] = [k for k, _ in parse_qsl(query, keep_blank_values=True)]
        pairs = [(k.strip().lower(), v) for k, v in parse_qsl(query, keep_blank_values=True)]
        request.scope["query_string"] = urlencode(pairs).encode("latin-1")
    return await call_next(request)
app.include_router(admin.router)
app.include_router(produtos.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
