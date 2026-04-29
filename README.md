# Epi Meta Extractor

Epi Meta Extractor is a full-stack application for turning epidemiology study PDFs into structured, reviewable metadata for systematic reviews and meta-analyses.

The current codebase consists of:
- a FastAPI backend for PDF ingestion, LLM extraction, batch processing, auth, and export
- a Next.js frontend for authentication, project setup, uploads, progress tracking, and results review
- **GROBID** for structured scientific PDF parsing (metadata, sections, references)
- MongoDB for study/project storage
- Qdrant for optional semantic search over embeddings

## Repository Layout

```text
backend/     FastAPI app, services, schemas, tests
frontend/    Next.js app
docs/        architecture, setup, testing, and reference material
scripts/     manual helpers and one-off local test scripts
data/        uploaded PDFs in local development
tmp/         temporary processing artifacts
```

## Core Workflow

1. Sign in with a magic link.
2. Create or select a meta-analysis project.
3. Choose an effect measure.
4. Upload a PDF or ZIP of PDFs.
5. Extract study metadata and effect data with the backend pipeline.
6. Review results and export them as CSV.

## Local Development

### Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn backend.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8001` unless `NEXT_PUBLIC_API_URL` is set.

### Supporting Services

Start MongoDB, Qdrant, and GROBID with Docker:

```bash
docker compose up -d mongodb qdrant grobid
```

**Note:** GROBID requires at least 4GB RAM allocated to Docker. It may take 60-90 seconds to fully start on first run.

## Testing

Run the backend test suite:

```bash
pytest
```

Tests are currently scoped to `backend/tests`.

## Documentation

- [Docs index](docs/README.md)
- [Architecture overview](docs/architecture/overview.md)
- [API reference](docs/reference/api.md)
- [Backend setup](docs/setup/BACKEND_SETUP.md)

## Notes

- The repository is configured for local-development defaults. Review [backend/config.py](backend/config.py) and environment variables before deploying anywhere persistent.
- Embeddings and some extraction paths depend on external model/provider credentials.
