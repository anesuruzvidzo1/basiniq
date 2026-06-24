# BasinIQ

Natural language interface for Alberta's upstream energy sector. Ask questions about AER regulatory directives and well license data in plain English — get cited, structured answers in seconds.

**Live demo:** [basiniq.vercel.app](https://basiniq.vercel.app)

---

## What it does

BasinIQ combines two data sources:

- **AER Regulatory Directives** — 8 directives covering drilling, waste management, flaring, noise control, emergency planning, and measurement requirements (392 indexed chunks)
- **Well License & Production Data** — 200+ synthetic wells with 2,520 production records across Alberta formations and regions

A natural language query runs hybrid retrieval against both sources simultaneously and returns a structured answer with page-level citations.

Example queries:

- *"How many active Montney wells does Tourmaline have, and what flaring rules apply?"*
- *"What are the noise control requirements for well sites near residences?"*
- *"What waste management procedures apply to drilling operations in Alberta?"*

---

## Architecture

```
Next.js (Vercel)
    │
    ▼
FastAPI (async)
    │
    ├── query_wells ──► PostgreSQL + pgvector
    │                   SQL query on wells / production tables
    │
    └── search_documents ──► Elasticsearch (BM25)
                         ──► pgvector (dense 384-dim embeddings)
                             │
                             └── Reciprocal Rank Fusion
                                 │
                                 └── Cross-encoder reranking
                                     │
                                     └── Top 5 chunks → Claude (tool use loop)
```

**Retrieval pipeline:**
1. BM25 keyword search (Elasticsearch) and dense semantic search (pgvector) run in parallel
2. Results merged with Reciprocal Rank Fusion
3. Top candidates reranked with a cross-encoder (`ms-marco-MiniLM-L-6-v2`)
4. Top 5 chunks passed to Claude as tool results
5. Claude synthesizes the answer with citations

**Multi-turn conversation** — session history persisted in PostgreSQL JSONB. Follow-up questions carry full context without restating it.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, Tailwind CSS v4, React Markdown |
| API | FastAPI, async SQLAlchemy, asyncpg |
| Vector search | pgvector (cosine similarity, 384-dim) |
| Keyword search | Elasticsearch 8.13 (BM25, English analyzer) |
| Embeddings | `all-MiniLM-L6-v2` (bi-encoder) |
| Reranking | `ms-marco-MiniLM-L-6-v2` (cross-encoder) |
| LLM | Claude (tool use agentic loop) |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose |

---

## Run locally

**Prerequisites:** Docker, Docker Compose, an Anthropic API key

```bash
git clone https://github.com/anesuruzvidzo1/basiniq.git
cd basiniq
```

Create `.env` in the project root:

```env
POSTGRES_USER=basiniq
POSTGRES_PASSWORD=basiniq
POSTGRES_DB=basiniq
POSTGRES_HOST=db
POSTGRES_PORT=5432
ELASTICSEARCH_URL=http://elasticsearch:9200
ANTHROPIC_API_KEY=sk-ant-...
```

Start all services:

```bash
docker compose up -d
```

Seed the well database:

```bash
docker exec -it basiniq-api-1 python seed.py
```

Ingest AER directives:

```bash
docker exec -it basiniq-api-1 python ingest_docs.py
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## AER Directives indexed

| Directive | Topic |
|---|---|
| Directive 001 | Requirements for Controlling Emissions from Hydrocarbon Flaring |
| Directive 038 | Noise Control |
| Directive 047 | Oilfield Waste Management Facilities |
| Directive 050 | Drilling Waste Management |
| Directive 056 | Energy Conservation Requirements |
| Directive 060 | Upstream Petroleum Industry Flaring, Incinerating and Venting |
| Directive 071 | Emergency Preparedness and Response |
| Directive 083 | Measurement Requirements for Oil and Gas Operations |

---

## Demo note

Well data is synthetic. AER directives are publicly available documents from the Alberta Energy Regulator. This tool is intended as a research aid — verify all regulatory requirements directly with the AER before making compliance decisions.

---

Built by [Anesu Ruzvidzo](https://github.com/anesuruzvidzo1)
