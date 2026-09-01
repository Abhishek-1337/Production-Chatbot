from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.user import User
from schemas.auth import Token, UserResponse, CreateUserRequest, RegisterResponse, LoginRequest
from services.auth import get_current_user
from api.v1.controllers.auth import (
    register_controller,
    login_controller,
    google_login_controller,
    google_callback_controller,
    google_logout_controller,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    user_data: CreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await register_controller(user_data, db)


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await login_controller(credentials, db)


@router.get("/google/login", include_in_schema=False)
async def google_login() -> RedirectResponse:
    return await google_login_controller()


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str | None = None,
) -> RedirectResponse:
    return await google_callback_controller(code, db)


@router.get("/google/logout", include_in_schema=False)
async def google_logout() -> JSONResponse:
    return await google_logout_controller()


@router.post("/logout", include_in_schema=False)
async def logout() -> JSONResponse:
    return await google_logout_controller()


@router.post("/google/logout", include_in_schema=False)
async def google_logout_post() -> JSONResponse:
    return await google_logout_controller()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
