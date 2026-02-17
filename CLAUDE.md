# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Policy

All code in this project must be written in **Python**, except for `data-fetcher/` which uses Node.js/TypeScript (required by the `israeli-bank-scrapers` npm package). This includes scrapers, ingestion, services, API routes, scripts, and any new modules.

## Project Overview

**Cashboard** — a personal finance manager with two independent sub-projects:

- **`backend/`** — Python/FastAPI REST API with SQLite (raw `sqlite3`, no ORM)
- **`data-fetcher/`** — Node.js/TypeScript bank scraper using `israeli-bank-scrapers` (only exception to the Python-only rule)
- **`plan/`** — Design docs, mockups, and implementation roadmap (`Backend_Tasks.md`)

## Commands

### Backend (Python/FastAPI)

```bash
# Run the API server (from repo root)
cd backend && uvicorn api.app:app --reload

# Initialize/reset the database
cd backend && python -c "from db.database import init_db; init_db()"

# Install dependencies
cd backend && pip install -r requirements.txt
```

### Data Fetcher (Node.js/TypeScript)

```bash
cd data-fetcher && npm install
cd data-fetcher && npm run scrape:all      # all banks
cd data-fetcher && npm run scrape:leumi    # single bank
cd data-fetcher && npm run scrape:isracard
cd data-fetcher && npm run scrape:max
```

### No test infrastructure exists yet

There are no test frameworks, test directories, or test files configured.

## Architecture

### Backend Pattern

All routes follow the same structure:
- `api/app.py` — FastAPI entry point, registers routers, calls `init_db()` on startup
- `api/models.py` — Pydantic request/response schemas for all entities
- `api/routes/<entity>.py` — Each route file uses `APIRouter` with prefix `/api/<resource>`, `Depends(get_db)` for DB connections, raw SQL queries
- `db/database.py` — Connection management with `get_connection()` and `get_db()` FastAPI dependency
- `config.py` — `DB_PATH` from `CASHBOARD_DB_PATH` env var (defaults to `backend/cashboard.db`)

### Database Conventions

- SQLite with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row` on every connection
- In-memory mode via shared-cache URI (`file:cashboard?mode=memory&cache=shared`) for testing — a `_keep_alive_conn` prevents the DB from being destroyed
- Schema is idempotent: `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE` in seed data
- `schema_version` table tracks migrations; currently at version 1
- Category id=1 ("Uncategorized") is permanently protected — never delete it
- Delete protection: accounts and credit cards check foreign key references before allowing deletion

### Data Fetcher Pattern

- `scrapers/scrape.ts` dispatches to bank-specific modules based on CLI arg
- Credentials from `.env` (see `.env.example`), validated at runtime
- Output: JSON files in `output/<bankname>/<bankname>_<date>.json`
- `patches/patch-isracard.js` runs on `postinstall` to fix a known scraper library issue

## Implementation Roadmap

See `plan/Backend_Tasks.md` for the full 6-phase plan. Current status:
- **Phase 1 (Foundation)**: Complete — DB setup + Settings CRUD for 7 entities
- **Phase 2 (Scraper & Data Pipeline)**: Next — ingestion, classification, transaction endpoints
- **Phases 3-6**: Pending — analytics, yearly views, wedding planner, frontend

## Key Files

- `backend/db/schema.sql` — All 13 table definitions with constraints and indexes
- `backend/db/seed.sql` — Default categories and Israeli merchant classification rules
- `backend/api/models.py` — All Pydantic models (look here before creating new ones)
- `plan/Backend_Tasks.md` — Detailed specs for every upcoming feature
- `plan/DB_Schema.md` — Database schema reference
