# BasinIQ

A RAG system built for Alberta's upstream energy sector. Ask questions in plain English — get structured answers with page-level citations sourced from AER regulatory directives and well license data.

Built as a portfolio project to demonstrate production-quality retrieval architecture in a domain where precision and citation matter. Live demo at [basiniq.vercel.app](https://basiniq.vercel.app).

---

## How it works

A query like "How many active Montney wells does Tourmaline have, and what flaring rules apply?" triggers a Claude tool use loop with two tools wired in:

- `query_wells` runs a SQL SELECT against a PostgreSQL database of licensed wells and production records
- `search_documents` runs hybrid retrieval over AER directive text

Hybrid retrieval combines BM25 keyword search (Elasticsearch) and dense vector search (pgvector, 384-dim cosine similarity), merges results using Reciprocal Rank Fusion, then reranks the top candidates with a cross-encoder. Top 5 chunks go to Claude as tool results. Multi-turn sessions are tracked in PostgreSQL JSONB — follow-up questions carry full context without restating it.

The frontend is a three-column layout: session sidebar, chat, and a live context panel showing which directive pages were cited.

---

## Retrieval pipeline

```
Query
  │
  ├── Elasticsearch (BM25)
  ├── pgvector (cosine, all-MiniLM-L6-v2)
  │
  └── Reciprocal Rank Fusion
        │
        └── ms-marco-MiniLM-L-6-v2 (cross-encoder rerank)
              │
              └── Top 5 chunks → Claude tool use loop
                    │
                    └── Structured answer with citations
```

---

## Stack

| | |
|---|---|
| Frontend | Next.js 16, Tailwind CSS v4, React Markdown |
| API | FastAPI, async SQLAlchemy, asyncpg |
| Vector search | pgvector (cosine similarity, 384-dim) |
| Keyword search | Elasticsearch 8.13, BM25, English analyzer |
| Embeddings | all-MiniLM-L6-v2 |
| Reranking | ms-marco-MiniLM-L-6-v2 |
| LLM | Claude (tool use agentic loop) |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose |

---

## AER directives indexed

| Directive | Topic |
|---|---|
| 001 | Requirements for Controlling Emissions from Hydrocarbon Flaring |
| 038 | Noise Control |
| 047 | Oilfield Waste Management Facilities |
| 050 | Drilling Waste Management |
| 056 | Energy Conservation Requirements |
| 060 | Upstream Petroleum Industry Flaring, Incinerating and Venting |
| 071 | Emergency Preparedness and Response |
| 083 | Measurement Requirements for Oil and Gas Operations |

392 indexed chunks across 8 directives. Well data is synthetic (200+ wells, 2,520 production records across Peace River, Pembina, Foothills, Red Deer, and Lloydminster).

---

## Run locally

Prerequisites: Docker, Docker Compose, Anthropic API key.

```bash
git clone https://github.com/anesuruzvidzo1/basiniq.git
cd basiniq
```

Create `.env` at the project root:

```
POSTGRES_USER=basiniq
POSTGRES_PASSWORD=basiniq
POSTGRES_DB=basiniq
POSTGRES_HOST=db
POSTGRES_PORT=5432
ELASTICSEARCH_URL=http://elasticsearch:9200
ANTHROPIC_API_KEY=sk-ant-...
```

Start the backend:

```bash
docker compose up -d
```

Seed the well database and ingest directives:

```bash
docker exec -it basiniq-api-1 python seed.py
docker exec -it basiniq-api-1 python ingest_docs.py
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Deployment (Railway + Vercel)

The root-level `Dockerfile` builds both the backend code and the data directory into one image, so Railway can run it without a separate volume mount.

Set these environment variables in Railway:

```
ANTHROPIC_API_KEY=...
ELASTICSEARCH_URL=...       # Bonsai.io free tier works
ALLOWED_ORIGINS=https://your-frontend.vercel.app
DATABASE_URL                # auto-wired by Railway PostgreSQL plugin
```

Deploy frontend to Vercel with `NEXT_PUBLIC_API_URL` set to the Railway service URL.

---

Well data is synthetic. Directive text is from public AER documents. Not a compliance tool — verify all regulatory requirements directly with the AER before making any compliance decisions.

Built by [Anesu Ruzvidzo](https://github.com/anesuruzvidzo1)
