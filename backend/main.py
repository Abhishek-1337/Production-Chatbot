from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from nemoguardrails import LLMRails, RailsConfig
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


@app.on_event("startup")
async def load_guardrails() -> None:
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    app.state.rails = LLMRails(config)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
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

    if isinstance(response, dict):
        content = response.get("content", "")
    else:
        content = response

    return ChatResponse(response=content)


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
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
