from datetime import datetime

from pydantic import BaseModel, Field


class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Quem vai usar a chave")


class KeyInfo(BaseModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool

    model_config = {"from_attributes": True}


class KeyCreated(KeyInfo):
    api_key: str = Field(description="Exibida apenas uma vez. Guarde em local seguro.")


class Produto(BaseModel):
    # Campos no formato de produto do catálogo VTEX.
    Id: int
    Name: str
    DepartmentId: int
    CategoryId: int
    BrandId: int
    LinkId: str
    RefId: str
    IsVisible: bool
    Description: str
    DescriptionShort: str
    ReleaseDate: str
    KeyWords: str
    Title: str
    IsActive: bool
    TaxCode: str
    MetaTagDescription: str
    SupplierId: int
    ShowWithoutStock: bool
    Score: int
    # Extras (na VTEX ficam nas APIs de SKU/preço), necessários para a IA responder ao cliente.
    Price: float
    Size: str
    # Quantidade por loja ({"centro": 2, ...}); fica só no JSON, a resposta usa "Stores".
    Stock: dict[str, int] = Field(default_factory=dict, exclude=True)


class Loja(BaseModel):
    Id: str
    Name: str
    Address: str


class EstoqueLoja(BaseModel):
    StoreId: str
    StoreName: str
    Quantity: int
    Availability: str


class ProdutoResposta(Produto):
    Availability: str = Field(
        description="'available' ou 'unavailable' (na loja filtrada, ou em pelo menos uma loja)"
    )
    Stores: list[EstoqueLoja]


class ListaProdutos(BaseModel):
    total: int
    # Ajudam a depurar a configuração da IA: o que a API entendeu e o que ela descartou.
    filtros_aplicados: dict[str, str] = Field(default_factory=dict)
    parametros_ignorados: list[str] = Field(default_factory=list)
    itens: list[ProdutoResposta]
