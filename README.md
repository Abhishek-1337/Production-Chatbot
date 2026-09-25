# Production Chatbot

A chatbot you can upload documents to and then ask questions about. You get answers streamed back live, and only you can see your own documents.

**The idea:** You upload PDFs, Word files, or text files. When you ask a question, the system finds the relevant pieces from your files and uses them to answer, instead of guessing. You stay logged in, your files stay private to you, and every answer is checked against basic safety rules.

**How it works:** You register and log in to get a token. You upload a document, which gets split into chunks and saved for searching. When you chat, you send a question with a document ID, the system pulls the most relevant chunks plus a short slice of recent conversation, builds a prompt, and streams the answer back sentence by sentence. Both your question and the answer are saved so you keep history.

**The bit that surprises people:** When your chat gets longer than 5 messages, the system does not just cut off old messages. It asks the AI to summarize the older part (up to 12 previous Q&As) and carries that summary forward. This keeps prompts small and cheap while still remembering context.

**What looks like a bug but isn't:** If the summary step fails, your chat still continues — just without the summary. This is deliberate. A missing summary is better than a blocked chat.

**When it breaks / goes blind:** If the AI service is rate-limited or times out, the request is retried with backoff. For search and history steps, failures fall back to answering with less context rather than erroring out.

**The switches you control:** You set your OpenAI key, database URL, and login secret in the env file. You can change how much history is kept verbatim versus summarized, which AI model is used, and how strict the safety checks are — smaller history and cheaper models cost less but remember less.

---

## What you get

- **Ask your documents** — upload PDF / DOCX / TXT, then ask questions. Search is always filtered to your user ID and document, so users never see each other's files.
- **Live answers** — chat streams over SSE with `start → token → done` events, so you see words as they generate.
- **Login** — passwords are hashed, auth is JWT bearer tokens on all private routes.
- **History that stays cheap** — keeps the last 5 messages word-for-word, summarizes older ones with the AI, with retry and fall back to no-summary if it fails.
- **Usage tracking + admin dashboard** — every query records how many tokens were used for chat, embeddings, and summaries. Admins see daily graphs, top users, and totals.
- **Safety checks** — prompt-injection and content moderation checks are wired into chat.
- **Versioned prompts** — separate templates for general chat and document-based chat.

---

## Tech Stack

| Layer | Technology |
|------------|-----------|
| API | FastAPI, uvicorn |
| AI / RAG | pydantic-ai, OpenAI (`gpt-4o-mini`), chromadb, chonkie |
| Guardrails | NeMo Guardrails |
| Database | PostgreSQL (asyncpg), SQLAlchemy 2.0 async, Alembic |
| Auth | JWT, bcrypt |
| Frontend | React 19, Recharts, Vite |

---

## Getting Started

### 1. Environment

Copy the example env file to `.env` inside backend and fill in:

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
```

Then visit `http://localhost:5173/admin` (admin sees dashboard, non-admin gets 403).

---

## API Endpoints (`/api/v1`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user |
| POST | `/auth/login` | No | Login → access token |
| GET | `/auth/me` | Yes | Current user |
| POST | `/document/upload` | Yes | Upload PDF/DOCX/TXT |
| POST | `/document/query` | Yes | Non-streamed doc Q&A |
| POST | `/chat/` | Yes | **Streamed (SSE)** doc Q&A |
| GET | `/admin/token-usage/daily` | Admin | Daily tokens (`?start=YYYY-MM-DD&end=YYYY-MM-DD&source=all\|llm\|embedding\|summary`) |
| GET | `/admin/token-usage/top-users` | Admin | Top N consumers per range (`?limit=10`) |
| GET | `/admin/token-usage/summary` | Admin | Totals: total/today/7d/30d + active users |
| GET | `/admin/token-usage/top-per-day` | Admin | Top consumer per day |
| GET | `/health` | No | Basic health check |

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

Both the user query and the streamed answer are saved to chat history.

---

## Production-Readiness Checklist

> What is done, partially done, and what remains.

### Completed ✅

- [x] **Streaming on chat** — answers stream token by token
- [x] **Secrets in env, not code** — API keys and DB URL come from env
- [x] **Per-user data isolation** — search and ownership checks filtered by user
- [x] **Retries on AI calls** — automatic retry with backoff on rate limits and timeouts
- [x] **History summarization** — short recent window kept verbatim, older chat summarized to bound token cost
- [x] **Cost tracking per request and per user** — token usage recorded per query by type (chat, embedding, summary)
- [x] **Admin token dashboard** — daily graph, top users bar chart + leaderboard, top-per-day table, date and source filters, summary cards

### Not Started ⬜

- [ ] **Fallback model chain configured**
- [ ] **Max token limits on input and output**
- [ ] **Timeout on all external calls (30s default)**
- [ ] **Load test with 100 concurrent users passing**

---

## Project Structure

- `backend/` — API entry point, async database setup, and migrations
- `backend/api/` — route definitions and business logic for auth, documents, chat, conversations, and admin
- `backend/models/` — database tables for users, documents, chat messages, conversations, and token usage
- `backend/schemas/` — request/response validation
- `backend/services/` — auth, file parsing, ingestion, search, prompts, and usage tracking
- `backend/scripts/` — helper to seed the first admin
- `backend/config/` — safety rails configuration
- `frontend/` — chat UI plus admin analytics page with charts
