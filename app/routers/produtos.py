from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.products import load_products, normalize
from app.schemas import ListaProdutos, Produto
from app.security import require_api_key

router = APIRouter(prefix="/produtos", tags=["produtos"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=ListaProdutos)
def listar_produtos(
    busca: str | None = Query(None, description="Palavras no nome (todas precisam aparecer)"),
    categoria: int | None = Query(None, description="CategoryId"),
    tamanho: str | None = Query(None, description="Size, ex.: 37"),
    ref_id: str | None = Query(None, description="RefId, ex.: S596L5012"),
    preco_min: float | None = Query(None, ge=0),
    preco_max: float | None = Query(None, ge=0),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    produtos = [p for p in load_products() if p.IsActive and p.IsVisible]

    if busca:
        termos = normalize(busca).split()
        produtos = [
            p for p in produtos
            if all(t in normalize(f"{p.Name} {p.KeyWords}") for t in termos)
        ]
    if categoria is not None:
        produtos = [p for p in produtos if p.CategoryId == categoria]
    if tamanho:
        produtos = [p for p in produtos if normalize(p.Size) == normalize(tamanho)]
    if ref_id:
        produtos = [p for p in produtos if p.RefId.upper() == ref_id.upper()]
    if preco_min is not None:
        produtos = [p for p in produtos if p.Price >= preco_min]
    if preco_max is not None:
        produtos = [p for p in produtos if p.Price <= preco_max]

    return ListaProdutos(total=len(produtos), itens=produtos[offset : offset + limite])


@router.get("/{produto_id}", response_model=Produto)
def obter_produto(produto_id: int):
    for p in load_products():
        if p.Id == produto_id:
            return p
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
