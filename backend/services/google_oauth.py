import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode

import bcrypt
import httpx
from dotenv import load_dotenv
from jose import jwt, jwk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_SCOPES = "openid email profile"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/api/v1/auth/google/callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

GOOGLE_COOKIE_NAME = "google_id_token"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

_certs_cache: dict = {}
_certs_fetched_at = 0.0
_CERTS_TTL = 3600.0


def get_google_login_url(state: str | None = None) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def _get_google_certs() -> dict:
    global _certs_cache, _certs_fetched_at
    now = time.monotonic()
    if _certs_cache and now - _certs_fetched_at < _CERTS_TTL:
        return _certs_cache
    async with httpx.AsyncClient() as client:
        response = await client.get(GOOGLE_CERTS_URL)
        response.raise_for_status()
        data = response.json()
    # Google returns {"keys": [{"kid": "...", "kty": "RSA", ...}, ...]}
    keys = data.get("keys", []) if isinstance(data, dict) else []
    _certs_cache = {k["kid"]: k for k in keys if "kid" in k}
    _certs_fetched_at = now
    return _certs_cache


async def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google-issued id_token against Google's public keys."""
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    if not kid:
        raise ValueError("Missing key id in token header")
    certs = await _get_google_certs()
    jwk_dict = certs.get(kid)
    if not jwk_dict:
        raise ValueError("Unknown Google signing key id")
    key = jwk.construct(jwk_dict, algorithm="RS256")
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=GOOGLE_CLIENT_ID or None,
        options={"verify_at_hash": False},
    )
    iss = claims.get("iss")
    if iss not in GOOGLE_ISSUERS:
        raise ValueError(f"Invalid issuer: {iss}")
    return claims


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    return result.scalar_one_or_none()


async def get_or_create_google_user(
    db: AsyncSession, email: str, name: str, google_sub: str | None = None
) -> User:
    # 1) stable lookup by Google sub (never changes, not affected by email change)
    if google_sub:
        existing = await get_user_by_google_sub(db, google_sub)
        if existing:
            return existing

    # 2) fallback by email — also links an existing password account to Google
    user = await get_user_by_email(db, email)
    if user:
        if google_sub and not user.google_sub:
            user.google_sub = google_sub
            await db.commit()
            await db.refresh(user)
        return user

    user = User(
        name=name or email.split("@")[0],
        email=email,
        google_sub=google_sub,
        password=bcrypt.hashpw(uuid.uuid4().hex.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
