from contextlib import asynccontextmanager

from fastapi import FastAPI
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
app.include_router(admin.router)
app.include_router(produtos.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
