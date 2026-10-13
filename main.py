# Ponto de entrada: `fastapi dev main.py` ou `uvicorn main:app --reload`
from app.main import app

__all__ = ["app"]
