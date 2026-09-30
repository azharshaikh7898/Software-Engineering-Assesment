# DocuMind: Design

## 1. Requirements and assumptions
- Users sign up, upload PDF/TXT/MD (max 10 MB), ask questions, get cited answers.
- Ingestion is asynchronous. Answers come only from the user's own documents.
- Assumptions: English documents, small corpora (hundreds of docs per user), free-tier LLM.

## 2. Architecture
```mermaid
flowchart LR
  U[Browser UI] -->|HTTPS| C[Caddy]
  C --> A[FastAPI API]
  A -->|SQL + vector search| P[(Postgres + pgvector)]
  A -->|enqueue + rate limit| R[(Redis)]
  R --> W[RQ worker]
  W -->|chunks + embeddings| P
  A -->|prompt with excerpts| L[LLM API]
```

## 3. API contract
| Method | Path | Body / response |
|---|---|---|
| POST | /auth/signup, /auth/login | `{username,password}` -> `{access_token}` |
| POST | /documents | multipart file -> 202 `{id,filename,status}` |
| GET | /documents, /documents/{id} | status: queued/processing/ready/failed (+error) |
| DELETE | /documents/{id} | 204; chunks removed by FK cascade |
| POST | /ask | `{question, document_ids?}` -> `{answer, refused, citations[], usage{}}` |
| GET | /history | last 50 answers |
| GET | /health, /livez | dependency status (db, vector_store, queue, worker) |

## 4. Data model
users(id, username, password_hash) - documents(id uuid, user_id, filename, status, error, content) -
chunks(id, document_id, user_id, idx, page, content, embedding vector(384)) -
queries(id, user_id, question, answer, refused, citations json, tokens, latency_ms, cost_usd).
Every query filters by user_id; document IDs are UUIDs and 404 (not 403) for other users.

## 5. Key trade-offs
- pgvector over a separate vector DB: one service, transactional deletes, filter by user in SQL.
- Local embedding model (bge-small, 384-d): no API key, no rate limit, deterministic. Costs image size and RAM.
- Paragraph-aware chunks (~800 chars, 120 overlap): keeps passages readable as citations.
- Refusal has two gates: similarity threshold before the LLM, and a NOT_FOUND sentinel from the LLM.
- Prompt injection: excerpts wrapped as untrusted data, delimiter tags stripped from content, system rules say never follow excerpt instructions.
- RQ over Celery: much less configuration. Redis also backs the rate limiter.
- create_all at startup instead of migrations: fine for v1, Alembic is the next step.

## 6. Changes after implementation
(fill in at the end)
