# QR_RAG — QR-driven Event Feedback + RAG Insights (FastAPI + Postgres + Chroma)

QR_RAG is a practical **QR → feedback → semantic search → RAG insights** proof-of-concept for events.

Organizers generate a QR code for an `event_id`, attendees submit short feedback from their phones, and organizers can ask natural-language questions to get **grounded summaries + recommended actions** based on the collected responses.

## Why this project

Post-event feedback is often scattered (forms, chats, spreadsheets). I wanted a lightweight system that:
- captures feedback instantly via QR
- stores it reliably
- enables **semantic retrieval** (not just keyword search)
- turns retrieved feedback into **actionable insights** for the organizer

## What I built

- **QR-based event flow**
  - Generate QR for an event: `GET /generate_qr/{event_id}`
  - Mobile-friendly feedback form: `GET /form/{event_id}`
  - Submission endpoint (stores feedback): `POST /submit/`

- **Feedback storage**
  - PostgreSQL persists all submissions by `event_id`

- **Embeddings + Vector index**
  - Each feedback summary is embedded using OpenAI embeddings (`text-embedding-3-small`)
  - Stored in a persistent Chroma collection with metadata (e.g., `event_id`, `name`)

- **Organizer chat (RAG-style)**
  - Organizer UI: `GET /organizer/chat/{event_id}`
  - Ask questions: `POST /chat/{event_id}`
  - Retrieves top-k relevant feedback snippets (event-scoped) and uses an LLM to generate:
    - key themes
    - recommended immediate actions
    - improvements for the next event

- **Basic analytics**
  - Total registrations: `GET /analytics/{event_id}/total`

## Example queries

- “What did participants like the most?”
- “Any complaints about the venue or food?”
- “What should we improve for the next event?”

## Architecture (high-level)

1. Organizer generates QR for `event_id`
2. Attendee scans QR → opens form → submits feedback
3. App saves submission in Postgres
4. App creates an embedding and upserts into Chroma (with `event_id`)
5. Organizer asks a question → app retrieves relevant feedback → LLM generates an answer grounded in those snippets

## Tech stack

- **Backend**: FastAPI, Uvicorn
- **UI**: Jinja2 templates (simple organizer + attendee pages)
- **Database**: PostgreSQL (Docker image: `pgvector/pgvector:pg16`)
- **Vector store**: ChromaDB (persistent local volume)
- **LLM + Embeddings**: OpenAI API
- **Containerization**: Docker + Docker Compose

## Run with Docker

### Prerequisites
- Docker Desktop installed

### 1) Configure environment

Edit `.env` and set at least:
- `API_KEY=<your_openai_api_key>`
- `SECRET_KEY=<your_secret_key>`
- `ALGORITHM=HS256`

Optional:
- `APP_HOST=http://<your-laptop-ip>:8000` (important if you scan QR from your phone)
- `TOP_K=8`

### 2) Start services

```bash
docker compose up --build
```

### 3) Open the app

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

Try this end-to-end:
- Generate QR: `http://localhost:8000/generate_qr/1`
- Open form directly: `http://localhost:8000/form/1`
- Organizer chat UI: `http://localhost:8000/organizer/chat/1`

### 4) Stop

```bash
docker compose down
```

To also remove persistent DB/Chroma volumes:

```bash
docker compose down -v
```

## Notes / learnings

- Vector search retrieves **similar snippets**, not “the answer”.
- RAG works best when you combine retrieval with **generation** (LLM) to produce a clear, human-readable response.
- Scoping retrieval by `event_id` keeps results relevant and avoids cross-event contamination.

## Limitations

- Minimal auth (POC-level)
- Basic UI and analytics
- No hybrid search (keyword + vector) yet

## Next steps

- Hybrid search (BM25 + vectors)
- Reranking for better relevance
- Better dashboards (themes over time, top complaints, export)
- Multi-tenant auth (organizers / events)

---

If you use this or have ideas to improve it, feel free to open an issue or reach out.

