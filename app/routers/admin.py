from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey
from app.schemas import KeyCreate, KeyCreated, KeyInfo
from app.security import generate_key, hash_key, require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/keys", response_model=KeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(body: KeyCreate, db: Session = Depends(get_db)):
    raw_key = generate_key()
    key = ApiKey(name=body.name, prefix=raw_key[:10], key_hash=hash_key(raw_key))
    db.add(key)
    db.commit()
    return KeyCreated(**KeyInfo.model_validate(key).model_dump(), api_key=raw_key)


@router.get("/keys", response_model=list[KeyInfo])
def list_keys(db: Session = Depends(get_db)):
    return db.scalars(select(ApiKey).order_by(ApiKey.id)).all()


@router.delete("/keys/{key_id}", response_model=KeyInfo)
def revoke_key(key_id: int, db: Session = Depends(get_db)):
    key = db.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chave não encontrada")
    key.revoked = True
    db.commit()
    return key
