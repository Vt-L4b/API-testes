from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.products import find_store, load_products, load_stores, normalize, with_availability
from app.schemas import ListaProdutos, Loja, ProdutoResposta
from app.security import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


def _number(name: str, value: str | None, cast: type[int] | type[float]):
    # A IA pode montar a URL com variáveis vazias (ex.: "preco_max="): tratamos como "sem filtro".
    if value is None or not value.strip():
        return None
    try:
        return cast(value.strip().replace(",", "."))
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Valor inválido para '{name}': {value}"
        )


def _bool(name: str, value: str | None) -> bool | None:
    if value is None or not value.strip():
        return None
    value = normalize(value.strip())
    if value in ("true", "1", "sim", "s"):
        return True
    if value in ("false", "0", "nao", "n"):
        return False
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT, f"Valor inválido para '{name}': {value}"
    )


def _store(loja: str | None):
    if loja is None or not loja.strip():
        return None
    store = find_store(loja)
    if store is None:
        # Mensagem pensada para a IA: diz quais lojas existem.
        nomes = ", ".join(s.Name for s in load_stores())
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Loja '{loja}' não encontrada. Lojas existentes: {nomes}"
        )
    return store


@router.get("/lojas", response_model=list[Loja], tags=["lojas"])
def listar_lojas():
    return load_stores()


FILTROS = ("busca", "loja", "disponivel", "categoria", "tamanho", "ref_id", "preco_min", "preco_max")
PAGINACAO = ("limite", "offset")


@router.get("/produtos", response_model=ListaProdutos, tags=["produtos"])
def listar_produtos(
    request: Request,
    busca: str | None = Query(None, description="Palavras no nome (todas precisam aparecer)"),
    loja: str | None = Query(None, description="Loja (Id ou nome, ex.: norte, Shopping Norte)"),
    disponivel: str | None = Query(None, description="true: só disponíveis; false: só indisponíveis"),
    categoria: str | None = Query(None, description="CategoryId, ex.: 10"),
    tamanho: str | None = Query(None, description="Size, ex.: 37"),
    ref_id: str | None = Query(None, description="RefId, ex.: S596L5012"),
    preco_min: str | None = Query(None, description="Ex.: 100 ou 99,90"),
    preco_max: str | None = Query(None, description="Ex.: 300 ou 299,90"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    store = _store(loja)
    disponivel = _bool("disponivel", disponivel)
    categoria = _number("categoria", categoria, int)
    preco_min = _number("preco_min", preco_min, float)
    preco_max = _number("preco_max", preco_max, float)
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

    itens = [with_availability(p, store) for p in produtos]
    if disponivel is not None:
        itens = [p for p in itens if (p.Availability == "available") == disponivel]

    aplicados = {
        k: v for k, v in request.query_params.items() if k in FILTROS and v.strip()
    }
    ignorados = [
        k for k in request.scope.get("original_query_keys", [])
        if k.strip().lower() not in FILTROS + PAGINACAO
    ]
    return ListaProdutos(
        total=len(itens),
        filtros_aplicados=aplicados,
        parametros_ignorados=ignorados,
        itens=itens[offset : offset + limite],
    )


@router.get("/produtos/{produto_id}", response_model=ProdutoResposta, tags=["produtos"])
def obter_produto(produto_id: int, loja: str | None = None):
    store = _store(loja)
    for p in load_products():
        if p.Id == produto_id:
            return with_availability(p, store)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
