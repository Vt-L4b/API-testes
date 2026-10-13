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


def test_get_by_id(client):
    headers = {"X-API-Key": create_key(client)["api_key"]}
    assert client.get("/produtos/1001", headers=headers).json()["RefId"] == "S596LJ050"
    assert client.get("/produtos/999", headers=headers).status_code == 404


def test_revoked_key_is_rejected(client):
    key = create_key(client)
    client.delete(f"/admin/keys/{key['id']}", headers=ADMIN)
    assert client.get("/produtos", headers={"X-API-Key": key["api_key"]}).status_code == 401
