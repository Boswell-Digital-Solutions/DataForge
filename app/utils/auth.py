from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.database import get_db
from app.models import models, schemas

load_dotenv()

# Accept JWT_SECRET_KEY as the canonical name too. Deployments (render.yaml)
# provision JWT_SECRET_KEY via generateValue, and app/config.py already falls
# back to it — keep this module consistent so production doesn't crash when only
# JWT_SECRET_KEY is set.
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or ""
if not SECRET_KEY:
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError(
            "SECRET_KEY must be set in production. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    # Non-production: generate an ephemeral random key rather than shipping a
    # predictable constant. Tokens won't survive a process restart, which is
    # acceptable for local dev/tests and avoids a known signing key in source.
    import secrets as _secrets
    import logging as _logging
    SECRET_KEY = _secrets.token_urlsafe(32)
    _logging.getLogger(__name__).warning(
        "SECRET_KEY not set; using an ephemeral per-process dev key. "
        "Set SECRET_KEY for stable tokens."
    )
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# passlib reads bcrypt.__about__.__version__ for version detection; bcrypt 4.x
# removed that attribute, so passlib logs a harmless AttributeError trace at
# backend load. Hashing still works — quiet the trace to keep logs clean.
import logging as _bcrypt_logging
_bcrypt_logging.getLogger("passlib").setLevel(_bcrypt_logging.ERROR)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Precomputed dummy hash so authentication runs bcrypt even when the username
# does not exist. This keeps response timing constant regardless of user
# existence, mitigating username enumeration via timing side channels.
_DUMMY_PASSWORD_HASH = pwd_context.hash("constant-time-placeholder")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    # Always run a bcrypt verification (against a dummy hash when the user is
    # absent) so timing does not reveal whether the username exists.
    hashed = user.hashed_password if user else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(password, hashed)
    if not user or not password_ok:
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    if token_data.username is None:
        raise credentials_exception

    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_pressforge_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Fail-closed authentication baseline for PressForge routes.

    Any active, authenticated DataForge user may currently access PressForge.
    This reuses get_current_user() (so the JWT is decoded and the user looked up
    exactly once) and only adds the active-user check. Returns 403 for inactive
    users — note get_current_active_user() returns 400, so PressForge keeps its
    own dependency rather than reusing that one.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user

async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """Optional authentication - returns user if authenticated, None otherwise."""
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
        user = get_user_by_username(db, username=username)
        return user if user and user.is_active else None
    except (JWTError, Exception):
        return None
