from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import Token, UserResponse, CreateUserRequest, LoginRequest
from services.auth import authenticate_user, create_access_token, create_user
from services.google_oauth import (
    FRONTEND_URL,
    GOOGLE_COOKIE_NAME,
    exchange_code_for_tokens,
    get_google_login_url,
    get_or_create_google_user,
    verify_google_id_token,
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


def _google_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(
        f"{FRONTEND_URL}/oauth/callback?error={quote(message)}",
        status_code=302,
    )


async def google_callback_controller(
    code: str | None,
    db: AsyncSession,
) -> RedirectResponse:
    if not code:
        return _google_error_redirect("Google sign-in was cancelled")

    try:
        tokens = await exchange_code_for_tokens(code)
        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("No id_token in Google token response")
        claims = await verify_google_id_token(id_token)
        email = claims.get("email")
        if not email:
            raise ValueError("Google account has no verified email")
        google_sub = claims.get("sub")
        await get_or_create_google_user(db, email, claims.get("name", ""), google_sub)
    except Exception:
        return _google_error_redirect("Google sign-in failed")

    response = RedirectResponse(FRONTEND_URL, status_code=302)
    response.set_cookie(
        GOOGLE_COOKIE_NAME,
        id_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=int(tokens.get("expires_in", 3600)),
        path="/",
    )
    return response


async def google_logout_controller() -> JSONResponse:
    response = JSONResponse({"detail": "signed out"})
    # delete must match path of the original cookie; samesite/secure are not
    # required for deletion matching but we set them for completeness
    response.delete_cookie(
        GOOGLE_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response
