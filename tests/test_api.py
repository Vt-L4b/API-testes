import os

os.environ["ADMIN_TOKEN"] = "admin-teste"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["API_KEYS"] = "tk_fixa1, tk_fixa2"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

ADMIN = {"X-Admin-Token": "admin-teste"}


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


def create_key(client):
    resp = client.post("/admin/keys", json={"name": "whizz"}, headers=ADMIN)
    assert resp.status_code == 201
    return resp.json()


def test_admin_requires_token(client):
    assert client.get("/admin/keys").status_code == 401
    assert client.get("/admin/keys", headers={"X-Admin-Token": "errado"}).status_code == 401


def test_key_is_shown_once(client):
    key = create_key(client)
    assert key["api_key"].startswith("tk_")
    assert "api_key" not in client.get("/admin/keys", headers=ADMIN).json()[0]


def test_produtos_require_key(client):
    assert client.get("/produtos").status_code == 401
    assert client.get("/produtos", headers={"X-API-Key": "tk_falsa"}).status_code == 401


def test_list_with_x_api_key(client):
    key = create_key(client)
    resp = client.get("/produtos", headers={"X-API-Key": key["api_key"]})
    assert resp.status_code == 200
    assert resp.json()["total"] == 63


def test_static_keys_from_env(client):
    assert client.get("/produtos", headers={"X-API-Key": "tk_fixa2"}).status_code == 200
    assert client.get("/produtos", headers={"X-API-Key": "tk_fixa3"}).status_code == 401


def test_list_with_bearer(client):
    key = create_key(client)
    resp = client.get("/produtos", headers={"Authorization": f"Bearer {key['api_key']}"})
    assert resp.status_code == 200


def test_filters(client):
    headers = {"X-API-Key": create_key(client)["api_key"]}
    # Sem acento e com palavras fora de ordem.
    resp = client.get("/produtos?busca=sandalia dourada&tamanho=37", headers=headers).json()
    assert [p["RefId"] for p in resp["itens"]] == ["S5869T724"]

    resp = client.get("/produtos?ref_id=s596l5012", headers=headers).json()
    assert sorted(p["Size"] for p in resp["itens"]) == ["35", "36"]

    resp = client.get("/produtos?busca=bolsa&preco_max=300", headers=headers).json()
    assert [p["Price"] for p in resp["itens"]] == [219.99]


def test_empty_filters_are_ignored(client):
    headers = {"X-API-Key": "tk_fixa1"}
    resp = client.get("/produtos?busca=bota&tamanho=37&categoria=&preco_min=&preco_max=", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] > 0
    assert client.get("/produtos?preco_max=299,90", headers=headers).status_code == 200
    assert client.get("/produtos?preco_max=caro", headers=headers).status_code == 422


def test_lojas(client):
    lojas = client.get("/lojas", headers={"X-API-Key": "tk_fixa1"}).json()
    assert [l["Id"] for l in lojas] == ["2168", "6664", "2146", "2156"]


def test_disponibilidade_por_loja(client):
    headers = {"X-API-Key": "tk_fixa1"}
    # Id 1001 tem estoque na Loja 2168 (5) e não tem na Loja 6664.
    p = client.get("/produtos/1001?loja=2168", headers=headers).json()
    assert p["Availability"] == "available"
    assert p["Stores"] == [{"StoreId": "2168", "StoreName": "Loja 2168",
                            "Quantity": 5, "Availability": "available"}]
    for loja in ["6664", "Loja 6664", "loja 6664", "LOJA 6664"]:
        p = client.get(f"/produtos/1001?loja={loja}", headers=headers).json()
        assert p["Availability"] == "unavailable"
        assert p["Stores"][0]["StoreId"] == "6664"


def test_esgotado_em_todas(client):
    headers = {"X-API-Key": "tk_fixa1"}
    p = client.get("/produtos/1006", headers=headers).json()
    assert p["Availability"] == "unavailable"
    assert len(p["Stores"]) == 4
    assert "Stock" not in p


def test_filtro_disponivel(client):
    headers = {"X-API-Key": "tk_fixa1"}
    todos = client.get("/produtos?loja=2146", headers=headers).json()["total"]
    sim = client.get("/produtos?loja=2146&disponivel=true", headers=headers).json()["total"]
    nao = client.get("/produtos?loja=2146&disponivel=false", headers=headers).json()["total"]
    assert (todos, sim + nao) == (63, 63)
    assert client.get("/produtos?disponivel=false", headers=headers).json()["total"] == 5


def test_loja_inexistente(client):
    resp = client.get("/produtos?loja=praia", headers={"X-API-Key": "tk_fixa1"})
    assert resp.status_code == 404
    assert "Loja 6664" in resp.json()["detail"]
    assert client.get("/produtos?loja=", headers={"X-API-Key": "tk_fixa1"}).status_code == 200


def test_get_by_id(client):
    headers = {"X-API-Key": create_key(client)["api_key"]}
    assert client.get("/produtos/1001", headers=headers).json()["RefId"] == "S596LJ050"
    assert client.get("/produtos/999", headers=headers).status_code == 404


def test_revoked_key_is_rejected(client):
    key = create_key(client)
    client.delete(f"/admin/keys/{key['id']}", headers=ADMIN)
    assert client.get("/produtos", headers={"X-API-Key": key["api_key"]}).status_code == 401


def test_codigo_incompleto_nao_casa(client):
    headers = {"X-API-Key": "tk_fixa1"}
    assert client.get("/produtos?loja=21", headers=headers).status_code == 404
    assert client.get("/produtos?loja=216", headers=headers).status_code == 404


def test_nomes_de_parametro_sem_diferenciar_maiusculas(client):
    headers = {"X-API-Key": "tk_fixa1"}
    resp = client.get("/produtos?Busca=bota&LOJA=2168&Tamanho=37", headers=headers).json()
    assert resp["total"] == 5
    assert resp["filtros_aplicados"] == {"busca": "bota", "loja": "2168", "tamanho": "37"}
    assert resp["parametros_ignorados"] == []


def test_parametro_desconhecido_e_reportado(client):
    headers = {"X-API-Key": "tk_fixa1"}
    resp = client.get("/produtos?Name=bota&loja=2168&tamanho=37", headers=headers).json()
    assert resp["total"] == 15
    assert resp["parametros_ignorados"] == ["Name"]


def test_chave_pela_url(client):
    resp = client.get("/produtos?busca=bota&api_key=tk_fixa1")
    assert resp.status_code == 200
    assert resp.json()["parametros_ignorados"] == []
    assert "api_key" not in resp.json()["filtros_aplicados"]
    assert client.get("/produtos?api_key=tk_errada").status_code == 401
