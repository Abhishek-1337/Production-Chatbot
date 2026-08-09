from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from services.auth import (
    Token,
    UserResponse,
    CreateUserRequest,
    RegisterResponse,
)
from api.v1.controllers.auth import register_controller, login_controller

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user(request: Request) -> User:
    return request.state.user


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    user_data: CreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await register_controller(user_data, db)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await login_controller(form_data, db)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
