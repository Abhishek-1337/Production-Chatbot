from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import Token, UserResponse, CreateUserRequest, LoginRequest
from services.auth import authenticate_user, create_access_token, create_user


async def register_controller(
    user_data: CreateUserRequest,
    db: AsyncSession,
) -> dict:
    user = await create_user(db, user_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "user": UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active,
        ),
        "access_token": access_token,
        "token_type": "bearer",
    }


async def login_controller(
    credentials: LoginRequest,
    db: AsyncSession,
) -> Token:
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
