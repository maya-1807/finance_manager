# Backend Tasks — Implementation Order

> Each phase and task is listed in the order it should be implemented.
> Later tasks may depend on earlier ones; dependencies are noted where relevant.

> **Language policy:** All code must be Python, except `data-fetcher/` (Node.js/TypeScript, required by `israeli-bank-scrapers`).

---

## Phase 1 — Foundation

### Task 1: Database Setup ✅
- Create SQLite database file (`cashboard.db`)
- Create all 13 tables with schemas, foreign keys, CHECK constraints, and indexes
  - accounts, credit_cards, transactions, categories, classification_rules, fixed_incomes, fixed_expenses, savings, balance_snapshots, wedding_vendors, wedding_payments, wedding_settings, scrape_log
- Indexes: `transactions.date`, `transactions.source_id`, `transactions.category_id`, `transactions.original_id`, `balance_snapshots.date`
- Seed default data: 11 categories (with "Uncategorized" as id=1), Israeli merchant classification rules
- Schema versioning mechanism (`schema_version` table) for future migrations
- `database.py`: `get_connection()`, `init_db()`, `get_schema_version()`, `set_schema_version()`

### Task 2: Settings CRUD API ✅
- FastAPI app setup with CORS middleware, `init_db()` on startup
- `get_db()` FastAPI dependency in `database.py`
- Pydantic request/response models for all 7 entities
- Full CRUD endpoints (GET list, GET by id, POST, PUT, DELETE) for:
  - Accounts — `/api/accounts`
  - Credit Cards — `/api/credit-cards`
  - Categories — `/api/categories`
  - Classification Rules — `/api/classification-rules`
  - Fixed Incomes — `/api/fixed-incomes`
  - Fixed Expenses — `/api/fixed-expenses`
  - Savings — `/api/savings`
- Delete protection:
  - Accounts: block if referenced by credit_cards, transactions, fixed_incomes, fixed_expenses, savings, or balance_snapshots
  - Credit Cards: block if referenced by transactions or fixed_expenses
  - Categories: block if referenced by transactions or classification_rules; never delete id=1

---

## Phase 2 — Scraper & Data Pipeline

### Task 3: Node.js Scraper Script
- Integration with `israeli-bank-scrapers` npm package
- Scraper script (`scrapers/scraper_runner.js`) that connects to:
  - Bank Leumi (shared account) — `CompanyTypes.leumi`
  - Max credit card — `CompanyTypes.max`
  - Additional cards as needed (Isracard/Cal)
- Credentials stored in `.env` (never committed); `.gitignore` excludes `.env` and `cashboard.db`
- Output: JSON files per source in `scrapers/output/`
- Error handling: network errors, auth failures, timeouts
- Retry logic with backoff for transient failures
- Continue scraping other sources if one fails

### Task 4: Transaction Ingestion Pipeline
- Read scraper JSON output → normalize to unified format:
  - ISO 8601 dates, consistent amount signs (negative=expense, positive=income)
  - Map scraper fields to DB transaction columns
  - Store `original_id` from scraper to enable dedup
- Extract account balance from scraper response → store in `balance_snapshots`
- Duplicate detection: check `original_id` before inserting
  - Handle edge cases: same transaction in bank + credit card statements, pending→completed transitions
- Installment handling: extract `installment_number` and `installment_total` from scraper data

### Task 5: Automatic Classification
- On each new transaction:
  1. Match description against `classification_rules` keywords → assign category, set `transaction_type = "variable_expense"`
  2. Match against `fixed_expenses` keywords → set `transaction_type = "fixed_expense"`
  3. Match against `fixed_incomes` keywords → set `transaction_type = "income"`
  4. No match → leave as uncategorized (`category_id = 1`)
- Credit card billing day logic:
  - Transaction before billing day → charged this month
  - Transaction after billing day → expected next month
  - Use `credit_cards.billing_day` to determine charged vs. expected status

### Task 6: Transaction Endpoints
- `GET /api/transactions?from=&to=&category=&account=` — filtered list
- `GET /api/transactions/uncategorized` — unclassified transactions
- `PUT /api/transactions/:id` — edit transaction (category, notes, amount)
- `PUT /api/transactions/:id/classify` — manually classify; optionally create a new classification rule from the assignment (e.g., "Café Joe" → Food creates rule `keyword="Café Joe", category=Food`)

### Task 7: Manual CSV Import
- CSV/Excel import endpoint for Pepper or sources without scraper support
- Parser that maps columns to the standard transaction format
- Feeds into the same ingestion pipeline (dedup + classification)

### Task 8: On-Demand Sync
- `POST /api/sync` endpoint — triggers scraper + ingestion on demand (called by UI sync button)
- Accepts optional `banks` list; defaults to all banks
- Runs `npm run scrape:<bank>` via subprocess for each bank, continues on failure
- Calls `ingest_all()` to process new JSON files + auto-classify
- Returns structured summary (per-bank scrape status + ingestion counts)
- Scrape results logged to `scrape_log` table (via existing ingestion pipeline)

---

## Phase 3 — Core Views & Analytics

### Task 9: Overview Endpoint
- `GET /api/overview`
  - Total balance across all accounts (from latest `balance_snapshots`)
  - Balance per account
  - Savings list with current amounts
  - Remaining monthly budget (total category budgets minus spent)

### Task 10: Monthly View Endpoint
- `GET /api/monthly?month=2026-02&account_id=all`
  - Opening and closing balance (from `balance_snapshots`, interpolate if missing)
  - Income breakdown (matched fixed_incomes + other income transactions)
  - Fixed expenses breakdown with paid/expected status (using billing day logic)
  - Savings deposits
  - Variable expenses by category (budget vs. actual)
  - Uncategorized transactions
  - End-of-month forecast:
    - Current balance + expected remaining income − expected remaining fixed expenses − estimated variable expenses (avg daily spend × remaining days)

### Task 11: Budget Tracking
- Per category: budget defined (`categories.monthly_budget`) vs. actual spent
- Overall: total budget vs. total spent
- Percentage used and remaining
- Exposed via the monthly view and overview endpoints

### Task 12: Trend Calculations
- `GET /api/monthly/trends?month=2026-02`
  - Per-category comparison vs. 3-month and 6-month rolling average
  - Overall expense trend (up/down/stable + percentage)
  - Previous month comparison
  - Budget compliance summary
- Unusual expense detection: flag transactions > 2× the category average

---

## Phase 4 — Yearly View & Advanced Analytics

### Task 13: Yearly View Endpoint
- `GET /api/yearly?year=2026`
  - Monthly table: income, expenses, balance per month
  - Annual totals
- `GET /api/yearly/trends?year=2026`
  - Annual trend direction
  - Most expensive months
  - Year-over-year comparison
  - Monthly averages
  - Fastest growing categories

### Task 14: Savings Tracking
- Determine how savings values update:
  - Option A: scrape from bank (if savings appear in scraper data)
  - Option B: manual update via Settings CRUD
- Track value changes over time for Overview screen

---

## Phase 5 — Wedding Planner

### Task 15: Wedding CRUD Endpoints
- Vendors: `GET/POST/PUT/DELETE /api/wedding/vendors`
- Payments: `GET/POST/PUT/DELETE /api/wedding/payments`
- Settings: `GET/PUT /api/wedding/settings` (single-row: guest counts, budget, dates)

### Task 16: Wedding Calculator
- `GET /api/wedding/summary`
  - Total cost, paid so far, remaining
  - Budget vs. actual
- `GET /api/wedding/calculator`
  - Pull current account balances
  - Calculate months until wedding
  - Project income: (months × monthly income) + estimated gifts + additional income
  - Project expenses: (months × monthly expenses) + remaining vendor payments + additional expenses
  - Result: projected balance before and after wedding with status indicator

---

## Phase 6 — Frontend
### Task 17: Build the UI on top of the API

---

## Project Structure

```
backend/
├── .env                          # Credentials (not in git)
├── .gitignore
├── config.py                     # App config (DB path, thresholds)
├── requirements.txt              # Python dependencies
│
├── db/
│   ├── database.py               # DB connection, init, get_db()
│   ├── schema.sql                # Table creation SQL
│   ├── seed.sql                  # Default categories + rules
│   └── migrations/               # Future schema changes
│
├── scrapers/
│   ├── scraper_runner.js          # Node.js scraper script
│   ├── package.json
│   └── output/                    # JSON output from scrapers
│
├── ingestion/
│   ├── ingest.py                  # Read scraper JSON → DB
│   ├── classifier.py              # Auto-classify transactions
│   ├── duplicate_checker.py       # Prevent duplicate transactions
│   └── csv_importer.py            # Manual CSV/Excel import
│
├── api/
│   ├── __init__.py
│   ├── app.py                     # FastAPI app entry point
│   ├── models.py                  # Pydantic request/response schemas
│   └── routes/
│       ├── __init__.py
│       ├── accounts.py
│       ├── credit_cards.py
│       ├── categories.py
│       ├── classification_rules.py
│       ├── fixed_incomes.py
│       ├── fixed_expenses.py
│       ├── savings.py
│       ├── transactions.py
│       ├── overview.py
│       ├── monthly.py
│       ├── yearly.py
│       └── wedding.py
│
└── services/
    ├── forecast.py                # End-of-month forecasting
    ├── trends.py                  # Trend calculations
    ├── budget.py                  # Budget tracking logic
    ├── anomaly.py                 # Unusual expense detection
    └── wedding_calculator.py      # Wedding financial projections
```
