# Production Chatbot

A production-grade RAG (Retrieval-Augmented Generation) chatbot backend built with **FastAPI**, **pydantic-ai**, **SQLAlchemy (async)**, **PostgreSQL**, and **ChromaDB**. Users upload documents, ask questions against them, and receive **streamed (SSE)** answers — with JWT auth, per-user document isolation, and prompt/output guardrails.

---

## What's Built (Resume Summary)

- **RAG over user documents** — PDF / DOCX / TXT ingestion with Chunked sentence-transformers embeddings stored in ChromaDB; retrieval filtered by `user_id + document_id` for strict per-user isolation.
- **Streaming responses (SSE)** — `/api/v1/chat/` streams answer tokens over `text/event-stream` using pydantic-ai's `agent.run_stream`, with `start → token → done` events. Non-blocking: LLM calls are awaited, and blocking ChromaDB work is offloaded to a thread.
- **JWT authentication** — bcrypt password hashing, `python-jose` tokens, `OAuth2PasswordBearer` protecting all routes.
- **Async SQLAlchemy + PostgreSQL** — Alembic-managed schema: `users`, `documents`, `chat_messages` (stores both user query and assistant reply).
- **Guardrails (partial)** — NeMo Guardrails self-check prompt-injection & content moderation rails are configured and wired into the legacy `/chat` endpoint.
- **Prompt management** — versioned prompt templates (`general_chat`, `rag`) in `services/prompt_management.py`.
- **Conversation history management** — `MAX_HISTORY_MESSAGES=5` verbatim window; when history exceeds 5, the preceding up to 12 Q&A (24 messages) are summarized via LLM (`_summarize_history` + `_get_history_context` in `backend/api/v1/controllers/chat_message.py:29-155`) with `retry_llm` and fail-open fallback, keeping prompts compact and grounded.
- **Clean layered architecture** — `Routes → Controllers → Services → Database`, Pydantic schemas, Alembic migrations. Deduplicated history fetching via shared `_fetch_ordered_messages()` helper (`chat_message.py:39`).

---

## Tech Stack

| Layer      | Technology |
|------------|-----------|
| API        | FastAPI, uvicorn |
| AI / RAG   | pydantic-ai, OpenAI (`gpt-4o-mini`), chromadb, chonkie |
| Guardrails | NeMo Guardrails |
| Database   | PostgreSQL (asyncpg), SQLAlchemy 2.0 async, Alembic |
| Auth       | JWT (python-jose), bcrypt |

---

## Getting Started

### 1. Environment

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_EXPIRE_MINUTES=60
```

### 2. Database

```bash
cd backend
alembic upgrade head
```

### 3. Run

```bash
cd backend
.venv/bin/uvicorn main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

---

## API Endpoints (`/api/v1`)

| Method | Path             | Auth | Description |
|--------|------------------|------|-------------|
| POST   | `/auth/register` | No   | Register user |
| POST   | `/auth/login`    | No   | Login → access token |
| GET    | `/auth/me`       | Yes  | Current user |
| POST   | `/document/upload` | Yes | Upload PDF/DOCX/TXT |
| POST   | `/document/query`  | Yes | Non-streamed doc Q&A |
| POST   | `/chat/`         | Yes  | **Streamed (SSE)** doc Q&A |
| GET    | `/health`        | No   | Basic health check |

### SSE Chat Example

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "What is the capital of France?", "document_id": "<doc-uuid>"}'
```

```text
data: {"event": "start"}
data: {"event": "token", "content": "The capital of France is Paris."}
data: {"event": "done"}
```

Both the user query and the streamed answer are persisted to `chat_messages`.

---

## Production-Readiness Checklist

> Resume-style status: what is done, partially done, and what remains.

### Completed ✅
- [x] **Streaming enabled for all chat endpoints** — SSE token streaming via pydantic-ai `run_stream`
- [x] **API keys stored in environment variables, not code** — `.env` + `.env.example`, `load_dotenv` (`OPENAI_API_KEY`, `DATABASE_URL`, `JWT_SECRET_KEY`)
- [x] **Per-user data isolation** — retrieval and ownership checks filtered by `user_id`
- [x] **Exponential backoff on all LLM API calls** — `tenacity` `retry_llm` / `retry_embedding` / `retry_vector_*` in `services/retry_utils.py` (LLM 429/timeout/5xx, fail-open elsewhere)
- [x] **Conversation history summarization** — `chat_message.py:29` window `5` + LLM summary of last `12` Q&A (`chat_message.py:79-155`) to bound prompt tokens

### In Progress 🟡
- [ ] **Input guardrails active (prompt injection, PII)** — config exists (`self_check_input`) and runs on legacy `/chat`; **not yet applied to the SSE RAG endpoint**
- [ ] **Output guardrails active (content filtering, format validation)** — config exists (`self_check_output`); same gap as above
- [ ] **Health check endpoint returning dependency status** — `/health` exists but only returns `{"status":"ok"}`, not DB/vector-store status
- [ ] **CORS configured for production domains only** — currently allows `http://localhost:3000` (dev) only
- [ ] **Structured logging with request IDs** — dependency `logger.info` exists in `alembic/env.py` only; no request-scoped logging middleware yet

### Not Started ⬜
- [ ] **Rate limiting per user (10–50 req/min default)**
- [ ] **Fallback model chain configured**
- [ ] **Cost tracking per request and per user**
- [ ] **Max token limits on input and output**
- [ ] **Timeout on all external calls (30s default)**
- [ ] **Load test with 100 concurrent users passing**

---

## Recent Changes

### 2026-08-23 — Delete feedback UX fix

- **fix(ui): show deleting state immediately on conversation delete** (`frontend/src/components/Sidebar.tsx:75-152`, `frontend/src/App.tsx:214-237`) — `ConversationCard` previously only rendered `Deleting…` inside the dropdown menu (`menuOpen && isDeleting`), which closed on `onDelete` (`setMenuOpen(false)`) so no feedback was visible during the async `api.deleteConversation` call. Fixed by rendering deleting state at the card level: `aria-busy` + `opacity-60`, left icon → spinner, inline `Deleting…` label next to title (alongside existing `Loading…` for `isSelecting`), and right-side spinner replacing the three-dot menu while `deletingId === conversation.id`; disabled `onSelect`/menu actions during delete. Added `loading` toast in `App.deleteConversation()` (mirroring `upload`) — `Deleting "title"…` → success/error — so global feedback is visible even when sidebar is collapsed.

### 2026-08-23 — Chat history summarization & DRY refactor

- **feat(chat): summarize history when exceeding 5 messages** (`backend/api/v1/controllers/chat_message.py:29`, `backend/api/v1/controllers/chat_message.py:79-155`) — `MAX_HISTORY_MESSAGES` reduced `12 → 5`; new `SUMMARY_QA_COUNT=12` / `SUMMARY_WINDOW_MESSAGES=24` / `SUMMARY_MAX_CHARS=12000`; added `@retry_llm _summarize_history()` and `_get_history_context()` (summary + verbatim recent 5, fail-open to truncated history); `chat_message_stream()` now uses `_get_history_context()` with fallback to `_get_conversation_history()`/`_format_conversation_history()`.
- **refactor(chat): deduplicate conversation history fetching** (`backend/api/v1/controllers/chat_message.py:39`) — extracted shared `async def _fetch_ordered_messages(conversation_id, current_query, db, limit)` (single `select … order_by(desc).limit` + `reversed` + `current_query` pop); `_get_conversation_history()` and `_get_history_context()` now delegate, removing duplicated 9-line fetch blocks.
- **docs: update README** — documented history window + summarization and DRY helper.

---

## Project Structure

```
backend/
├── main.py                      # FastAPI entry point
├── database.py                  # async engine / session / Base
├── alembic/                     # migrations
├── api/v1/
│   ├── controllers/             # business logic (auth, document, chat_message)
│   ├── routes/                  # route definitions
│   └── __init__.py              # router registration
├── models/                      # SQLAlchemy models (user, document, chat_message)
├── schemas/                     # Pydantic schemas
├── services/                    # auth, parser, ingest, doc_retrieval, prompt_management
├── config/guardrails_config/    # NeMo Guardrails rails
└── chroma_db/                   # vector store
```

See `backend/STRUCTURE.md` for the full architecture breakdown.
