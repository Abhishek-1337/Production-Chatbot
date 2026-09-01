import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.auth import CreateUserRequest
from services.google_oauth import (
    GOOGLE_COOKIE_NAME,
    get_user_by_email,
    get_user_by_google_sub,
    verify_google_id_token,
)

# This module is imported before main.py can load the backend-local env file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "360"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Password login: JWT bearer token
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str | None = payload.get("sub")
            if user_id:
                user_uuid = uuid.UUID(user_id)
                result = await db.execute(select(User).where(User.id == user_uuid))
                user = result.scalar_one_or_none()
                if user:
                    return user
        except (JWTError, ValueError):
            pass

    # Google login: id_token stored in an httpOnly cookie
    google_token = request.cookies.get(GOOGLE_COOKIE_NAME)
    if google_token:
        try:
            claims = await verify_google_id_token(google_token)
            google_sub = claims.get("sub")
            if google_sub:
                user = await get_user_by_google_sub(db, google_sub)
                if user:
                    return user
            email = claims.get("email")
            if email:
                user = await get_user_by_email(db, email)
                if user:
                    return user
        except Exception:
            pass

    raise credentials_exception


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def create_user(db: AsyncSession, user_data: CreateUserRequest) -> User:
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
