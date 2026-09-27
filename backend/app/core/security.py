"""Password hashing (PBKDF2, stdlib only) + JWT auth helpers."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

bearer = HTTPBearer(auto_error=False)

_ITER = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER)
    return f"pbkdf2${_ITER}${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, it, salt, hexd = hashed.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(it))
        return hmac.compare_digest(dk.hex(), hexd)
    except Exception:
        return False


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.JWT_SECRET, algorithm="HS256")


def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")


def require_db(db: Session = Depends(get_db)):
    return db
