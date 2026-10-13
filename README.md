# API de produtos para testes da Whizz

API em FastAPI que serve uma lista de produtos para a IA Whizz (Omnichat) consultar durante testes
com clientes. O acesso exige uma **chave** gerada por você, que pode ser revogada a qualquer momento.

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # defina um ADMIN_TOKEN forte
fastapi dev main.py         # http://127.0.0.1:8000/docs
```

Testes: `pytest -q`

## 1. Gerar a chave da Whizz

```powershell
curl.exe -X POST http://127.0.0.1:8000/admin/keys `
  -H "X-Admin-Token: SEU_ADMIN_TOKEN" -H "Content-Type: application/json" `
  -d '{\"name\": \"whizz\"}'
```

A resposta traz `api_key` (`tk_...`). **Ela só aparece uma vez**: no banco fica apenas o hash.

## 2. Requisição que a Whizz faz

```
GET /produtos?busca=cafe&disponivel=true
X-API-Key: tk_...
```

Também aceita `Authorization: Bearer tk_...`, caso a plataforma só permita esse formato.

### Filtros de `GET /produtos` (todos opcionais)

| Parâmetro | Exemplo | Descrição |
|---|---|---|
| `busca` | `sandalia dourada` | Palavras no nome (todas precisam aparecer; ignora acentos e maiúsculas) |
| `loja` | `norte` ou `Shopping Norte` | Disponibilidade só nessa loja (Id ou parte do nome) |
| `disponivel` | `true` | Só disponíveis (`false`: só indisponíveis) |
| `categoria` | `10` | `CategoryId` (tabela abaixo) |
| `tamanho` | `37` | `Size` (bolsas: `Único`) |
| `ref_id` | `S596L5012` | `RefId`; retorna todos os tamanhos do modelo |
| `preco_min` / `preco_max` | `100` | Faixa de preço |
| `limite` / `offset` | `20` / `0` | Paginação (padrão 50, máx. 200) |

Resposta: `{"total": N, "itens": [ ...produtos no formato VTEX... ]}`. Só retorna produtos com
`IsActive` e `IsVisible` verdadeiros.

`GET /produtos/{Id}` retorna um único produto (aceita `?loja=`). `GET /lojas` lista as lojas.

Cada produto vem com `Availability` (`available`/`unavailable`) e `Stores`: a quantidade em cada
loja, ou só na loja filtrada. Sem `loja`, `available` significa "tem em pelo menos uma loja".
Loja inexistente retorna 404 com a lista de lojas válidas.

## Lojas e estoque

As lojas ficam em `lojas.json`. O estoque fica no campo `Stock` de cada produto em `produtos.json`
(ex.: `"Stock": {"centro": 5, "norte": 0, "sul": 0, "outlet": 5}`); as chaves são os `Id` das
lojas. Esse campo não aparece na resposta, que usa `Stores`. Produtos com 0 em todas as lojas
aparecem como `unavailable`.

## Formato do produto

Segue o formato de produto do catálogo VTEX, com dois campos extras: `Price` e `Size`
(na VTEX eles ficam nas APIs de SKU/preço, mas a IA precisa deles para responder).
Cada tamanho é um item separado; o `RefId` agrupa os tamanhos do mesmo modelo.

| DepartmentId | | CategoryId | |
|---|---|---|---|
| 1 | Calçados | 10 Bota · 11 Ankle Boot · 12 Coturno | 20 Rasteira · 21 Sandália · 22 Tamanco · 23 Alpargata |
| 2 | Bolsas | 30 Sapatilha · 31 Mocassim · 32 Scarpin | 40 Tênis · 50 Bolsa |

## Rotas

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/produtos` | chave | Lista/busca produtos |
| GET | `/produtos/{id}` | chave | Detalhe de um produto |
| POST | `/admin/keys` | `X-Admin-Token` | Gera chave (valor exibido uma única vez) |
| GET | `/admin/keys` | `X-Admin-Token` | Lista chaves e último uso |
| DELETE | `/admin/keys/{id}` | `X-Admin-Token` | Revoga chave |
| GET | `/health` | — | Health check |

## Editar os produtos

Os produtos ficam em `produtos.json`. Edite o arquivo e reinicie o servidor.
O servidor recusa iniciar se algum produto estiver fora do formato.

## Deploy no Render

A Whizz roda nos servidores da Omnichat, então ela **não alcança `127.0.0.1`**: a API precisa
de uma URL pública. O `render.yaml` já descreve o serviço.

1. Publique este repositório no GitHub (pode ser privado).
2. No Render: **New → Blueprint**, conecte o GitHub e escolha o repositório.
3. Preencha as variáveis pedidas:
   - `ADMIN_TOKEN`: o mesmo do seu `.env` (ou outro token forte).
   - `API_KEYS`: a chave `tk_...` que a Whizz vai usar.
4. Após o deploy, a URL fica como `https://api-produtos-whizz.onrender.com`.

No plano gratuito o **banco SQLite é apagado a cada reinício**, por isso a chave da Whizz deve ficar
em `API_KEYS`, não só em `/admin/keys`. O serviço também **hiberna após ~15 min sem uso**: a primeira
requisição depois disso demora ~30–60 s. Para trocar/revogar a chave, edite `API_KEYS` no painel.
Não divulgue o `ADMIN_TOKEN`.
