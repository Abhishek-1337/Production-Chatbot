from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from nemoguardrails import LLMRails, RailsConfig
from pydantic import BaseModel, Field

from api.v1 import api_router as v1_router
from schemas.auth import UserResponse
from services.auth import get_current_user

load_dotenv()

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

app.include_router(v1_router, prefix="/api/v1")

GUARDRAILS_CONFIG_PATH = BACKEND_DIR / "config" / "guardrails_config"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

class Query(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


@app.on_event("startup")
async def load_guardrails() -> None:
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    app.state.rails = LLMRails(config)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
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

