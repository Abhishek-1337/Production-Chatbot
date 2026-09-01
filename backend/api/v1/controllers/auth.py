from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import Token, UserResponse, CreateUserRequest, LoginRequest
from services.auth import authenticate_user, create_access_token, create_user
from services.google_oauth import (
    FRONTEND_URL,
    decode_google_id_token,
    exchange_code_for_tokens,
    get_google_login_url,
    get_or_create_google_user,
)


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


async def google_login_controller() -> RedirectResponse:
    return RedirectResponse(get_google_login_url(), status_code=302)


async def google_callback_controller(
    code: str | None,
    db: AsyncSession,
) -> RedirectResponse:
    if not code:
        return RedirectResponse(
            f"{FRONTEND_URL}/oauth/callback?error=Google sign-in was cancelled",
            status_code=302,
        )
    try:
        tokens = await exchange_code_for_tokens(code)
        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("No id_token in Google token response")
        claims = decode_google_id_token(id_token)
        email = claims.get("email")
        if not email or not claims.get("email_verified"):
            raise ValueError("Google account email is not verified")
        user = await get_or_create_google_user(db, email, claims.get("name", ""))
        access_token = create_access_token(data={"sub": str(user.id)})
        return RedirectResponse(
            f"{FRONTEND_URL}/oauth/callback?token={access_token}",
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            f"{FRONTEND_URL}/oauth/callback?error=Google sign-in failed",
            status_code=302,
        )
