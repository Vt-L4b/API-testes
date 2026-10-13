from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.database import Base, engine
from app.products import load_products
from app.routers import admin, produtos


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    load_products()  # falha já na inicialização se o JSON estiver inválido
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
