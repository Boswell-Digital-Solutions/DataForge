from datetime import timedelta
from uuid import uuid4
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models, schemas
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    get_password_hash,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
legacy_router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _build_token_response(user: models.User) -> dict[str, str]:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "jti": str(uuid4())},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


def _validate_registration_payload(payload: schemas.UserCreate) -> None:
    if "@" not in payload.email or "." not in payload.email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address",
        )

@router.post("/token", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint to get JWT access token.

    Use the token in subsequent requests:
    Authorization: Bearer <token>
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _build_token_response(user)


@legacy_router.post("/register", response_model=schemas.User)
async def register_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint for JSON-based user registration."""
    _validate_registration_payload(user_in)

    existing_user = (
        db.query(models.User)
        .filter(
            (models.User.username == user_in.username) |
            (models.User.email == user_in.email)
        )
        .first()
    )
    if existing_user:
        if (
            existing_user.username == user_in.username
            and existing_user.email == user_in.email
        ):
            existing_user.hashed_password = get_password_hash(user_in.password)
            existing_user.is_active = True
            existing_user.is_admin = user_in.is_admin
            db.commit()
            db.refresh(existing_user)
            return existing_user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_admin=user_in.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@legacy_router.post("/login", response_model=schemas.Token)
async def legacy_login(
    login_request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint for JSON-based login."""
    user = authenticate_user(db, login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _build_token_response(user)


@legacy_router.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    current_user: models.User = Depends(get_current_user),
):
    """Legacy compatibility endpoint for token refresh."""
    return _build_token_response(current_user)


@legacy_router.get("/me", response_model=schemas.User)
async def get_me(
    current_user: models.User = Depends(get_current_user),
):
    """Legacy compatibility endpoint for current user profile."""
    return current_user
