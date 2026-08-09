from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import Token, UserResponse, CreateUserRequest
from services.auth import authenticate_user, create_access_token, create_user


async def register_controller(
    user_data: CreateUserRequest,
    db: AsyncSession,
) -> dict:
    user = await create_user(db, user_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "user": UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            is_active=user.is_active,
        ),
        "access_token": access_token,
        "token_type": "bearer",
    }


async def login_controller(
    form_data: OAuth2PasswordRequestForm,
    db: AsyncSession,
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
