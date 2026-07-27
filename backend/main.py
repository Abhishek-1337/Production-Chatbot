import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from nemoguardrails import LLMRails, RailsConfig
from passlib.context import CryptContext
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).parent
load_dotenv(BACKEND_DIR / ".env")

origins = [
    "http://localhost:3000",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GUARDRAILS_CONFIG_PATH = BACKEND_DIR / "config" / "guardrails_config"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str


class UserInDB(User):
    hashed_password: str


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin123")
AUTH_PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


RESOLVED_AUTH_PASSWORD_HASH = AUTH_PASSWORD_HASH or get_password_hash(AUTH_PASSWORD)


def get_user(username: str) -> UserInDB | None:
    if username != AUTH_USERNAME:
        return None
    return UserInDB(
        username=AUTH_USERNAME,
        hashed_password=RESOLVED_AUTH_PASSWORD_HASH,
    )


def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as exc:
        raise credentials_exception from exc

    user = get_user(token_data.username or "")
    if user is None:
        raise credentials_exception
    return User(username=user.username)


@app.on_event("startup")
async def load_guardrails() -> None:
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    app.state.rails = LLMRails(config)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/auth/me", response_model=User)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        response = await app.state.rails.generate_async(
            messages=[{"role": "user", "content": request.message}]
        )
    except Exception as exc:
        if "OPENAI_API_KEY" in str(exc):
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY is not configured. Add it to backend/.env or export it before starting the server.",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    print(response)

    if isinstance(response, dict):
        content = response.get("content", "")
    else:
        content = response

    return ChatResponse(response=content)


@app.post("/upload")
async def upload_document(
    _current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    # if file.upload_type not in allowed_types:
    #     raise HTTPException(status = 400, description = "File type is not allowed")
    
    contents = await file.read()
    print(contents)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents),
    }
