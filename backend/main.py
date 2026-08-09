from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
from services import parser, ingest, doc_retrieval
from pydantic_ai import Agent
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from nemoguardrails import LLMRails, RailsConfig
from pydantic import BaseModel, Field

from api.v1 import api_router as v1_router
from schemas.auth import UserResponse
from services.auth import get_current_user
import database
import models

load_dotenv()

agent = Agent(
  'openai-chat:gpt-4o-mini',
  system_prompt="You are an expert internal company AI assistant. Your job is to answer user questions using ONLY the provided document context. If the context does not contain the answer, say 'I cannot find that in the documents.' Do not invent facts outside of the provided context.",
)

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


@app.post("/query")
def query_doc(data: Query, _current_user: Annotated[UserResponse, Depends(get_current_user)]):
    context = doc_retrieval.retrieve_the_doc(data.query.strip())
    print(context)
    user_prompt = f"Document context:\n{context}\n\nQuestion: {data.query.strip()}"
    result = agent.run_sync(user_prompt)
    return {
        "result": result.output
    }


@app.post("/upload")
def upload_document(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    try:
        allowed_types = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        }

        if file.content_type not in allowed_types:
            raise HTTPException(status=400, detail="File type is not allowed")

        print(file.content_type)
        text = parser.parser(file)
        ingest.ingest_doc(text)

        return {
            "message": "Document is successfully uploaded. You can start querying the data."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong"
        )
