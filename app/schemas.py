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


class ListaProdutos(BaseModel):
    total: int
    itens: list[Produto]
