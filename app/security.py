import hashlib
import logging
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    APIKeyHeader,
    APIKeyQuery,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ApiKey, utcnow

KEY_PREFIX = "tk_"

# Logger do uvicorn, para as mensagens aparecerem junto dos acessos no log do Render.
logger = logging.getLogger("uvicorn.error")

# Declarados como esquemas de segurança para aparecerem no botão "Authorize" do /docs.
admin_header = APIKeyHeader(name="X-Admin-Token", scheme_name="AdminToken", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="ChaveAPI", auto_error=False)
bearer = HTTPBearer(scheme_name="ChaveBearer", auto_error=False)
# Alternativa para plataformas que não repassam cabeçalhos: ?api_key=tk_...
# O valor é mascarado no log de acesso (ver RedactApiKey em app/main.py).
api_key_query = APIKeyQuery(name="api_key", scheme_name="ChaveURL", auto_error=False)


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(raw_key: str) -> str:
    # A chave tem 256 bits de entropia, então SHA-256 simples é suficiente.
    return hashlib.sha256(raw_key.encode()).hexdigest()


def require_admin(x_admin_token: str | None = Depends(admin_header)) -> None:
    if not x_admin_token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Envie o token de admin no cabeçalho X-Admin-Token"
        )
    if not secrets.compare_digest(x_admin_token, get_settings().admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de admin inválido")


def require_api_key(
    request: Request,
    x_api_key: str | None = Depends(api_key_header),
    authorization: HTTPAuthorizationCredentials | None = Depends(bearer),
    query_key: str | None = Depends(api_key_query),
    db: Session = Depends(get_db),
) -> None:
    # Aceita "X-API-Key: tk_...", "Authorization: Bearer tk_..." ou "?api_key=tk_...",
    # para se adaptar ao formato que a plataforma da IA conseguir enviar.
    raw_key = x_api_key or (authorization.credentials if authorization else None) or query_key
    raw_key = raw_key.strip() if raw_key else None
    if not raw_key:
        # Só os nomes dos cabeçalhos (nunca os valores), para descobrir o que a plataforma enviou.
        logger.warning("401: requisição sem chave. Cabeçalhos recebidos: %s",
                       ", ".join(sorted(request.headers.keys())))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave de acesso ausente")

    if any(secrets.compare_digest(raw_key, k) for k in get_settings().static_api_keys):
        return

    key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_key(raw_key)))
    if key is None or key.revoked:
        # Só o início da chave, para identificar qual foi enviada sem expô-la.
        logger.warning("401: chave não reconhecida (começa com %r, %d caracteres)",
                       raw_key[:7], len(raw_key))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave inválida ou revogada")

    key.last_used_at = utcnow()
    db.commit()
