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
- **Token usage tracking & admin dashboard** — per-query `token_usage` table (`user_id`, `conversation_id`, `source='llm'|'embedding'|'summary'`, `prompt/completion/total_tokens`) with `tiktoken` fallback; admin-only `/admin` dashboard (Recharts) showing daily tokens graph + top-N leaderboard (source & date-range filters).
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
| Frontend   | React 19, Recharts, Vite |

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

### 4. Create first admin (for `/admin` dashboard)

```bash
cd backend
.venv/bin/python scripts/make_admin.py admin@example.com
# or: SQL — UPDATE users SET is_admin=true WHERE email='admin@example.com';
```

Then visit `http://localhost:5173/admin` (admin sees dashboard, non-admin gets 403).

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
| GET    | `/admin/token-usage/daily`       | Admin | Daily tokens (date_trunc UTC, `?start=YYYY-MM-DD&end=YYYY-MM-DD&source=all\|llm\|embedding\|summary`) |
| GET    | `/admin/token-usage/top-users`   | Admin | Top N consumers per range (`?limit=10`) |
| GET    | `/admin/token-usage/summary`     | Admin | Totals: total/today/7d/30d + active users |
| GET    | `/admin/token-usage/top-per-day` | Admin | Top consumer per day |
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
- [x] **Cost tracking per request and per user** — `token_usage` table + `is_admin` role; per-query `llm`/`embedding`/`summary` rows via `services/token_usage_service.py:1` (uses `result.usage()` with tiktoken fallback); admin analytics endpoints at `api/v1/routes/admin.py:1`
- [x] **Admin token dashboard** — `/admin` route (`frontend/src/pages/AdminDashboard.tsx:1`) with Recharts: daily `AreaChart` (total/prompt/completion), top-10 `BarChart` + leaderboard table, top-per-day table, date range picker (default 30d) + source filter, summary cards (total/today/7d/30d)


### Not Started ⬜
- [ ] **Fallback model chain configured**
- [ ] **Max token limits on input and output**
- [ ] **Timeout on all external calls (30s default)**
- [ ] **Load test with 100 concurrent users passing**

---

## Project Structure

```
backend/
├── main.py                      # FastAPI entry point
├── database.py                  # async engine / session / Base
├── alembic/                     # migrations (72cadb3c5dd0_add_token_usage_and_is_admin)
├── api/v1/
│   ├── controllers/             # business logic (auth, document, chat_message, admin)
│   ├── routes/                  # route definitions (auth, document, chat_message, conversation, admin)
│   └── __init__.py              # router registration
├── models/                      # SQLAlchemy models (user, document, chat_message, conversation, token_usage)
├── schemas/                     # Pydantic schemas (auth now exposes is_admin)
├── services/                    # auth, parser, ingest, doc_retrieval, prompt_management, token_usage_service
├── scripts/make_admin.py        # seed first admin
├── config/guardrails_config/    # NeMo Guardrails rails
└── chroma_db/                   # vector store
frontend/
├── src/pages/AdminDashboard.tsx # /admin analytics page (Recharts)
└── ...
```

See `backend/STRUCTURE.md` for the full architecture breakdown.
