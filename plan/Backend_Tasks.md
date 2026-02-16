# Backend Tasks

## 1. Database Setup

### 1.1 Initialize SQLite Database
- Create the SQLite database file (`cashboard.db`)
- Create all tables with proper schemas, foreign keys, and indexes
- Tables include: accounts, credit_cards, transactions, categories, classification_rules, fixed_incomes, fixed_expenses, savings, balance_snapshots, wedding_vendors, wedding_payments, wedding_settings, scrape_log
- Add indexes on frequently queried columns: `transactions.date`, `transactions.source_id`, `transactions.category_id`, `transactions.original_id`, `balance_snapshots.date`

### 1.2 Seed Default Data
- Insert default expense categories (food, transport, entertainment, health, clothing, household, subscriptions, etc.)
- Insert default classification rules for common Israeli merchants
- Set up a default "Uncategorized" category

### 1.3 Database Migrations
- Create a versioning mechanism for schema changes over time
- Ability to add/modify columns without losing data

---

## 2. Scraper Integration

### 2.1 Connect to israeli-bank-scrapers (Node.js)
- Decide on integration method: subprocess or separate process writing JSON
- Scraper script that connects to:
  - Bank Leumi (shared account) — `CompanyTypes.leumi`
  - Max credit card — `CompanyTypes.max`
  - Additional credit cards as needed (Isracard/Cal)
- Pepper — TBD (manual import or Riseup intermediary)

### 2.2 Credential Management
- Store credentials securely using `.env` file
- Never commit credentials to version control
- `.gitignore` configured to exclude `.env` and `cashboard.db`

### 2.3 Scraper Scheduling
- Set up automated scraping (cron job or similar)
- Recommended: once daily or every few days
- Log each run to `scrape_log` table

### 2.4 Scraper Error Handling
- Handle scraper failures gracefully (network errors, auth failures, timeouts)
- Retry logic with backoff for transient failures
- Log errors to `scrape_log` with status and error message
- Continue scraping other sources if one source fails

### 2.5 Manual Data Import
- CSV/Excel import for Pepper or any other source without scraper support
- Parser that maps columns to the standard transaction format

---

## 3. Transaction Processing

### 3.1 Data Ingestion
- Read raw scraper output (JSON)
- Normalize to unified transaction format:
  - Consistent date format (ISO 8601)
  - Consistent amount sign convention (negative = expense, positive = income)
  - Map source fields to DB columns
- Store `original_id` from scraper to prevent duplicates
- Extract and store account balance from scraper response into `balance_snapshots` table

### 3.2 Duplicate Detection
- Before inserting, check if `original_id` already exists in DB
- Handle edge cases:
  - Same transaction appearing in both bank and credit card statements
  - Pending transactions that later become completed

### 3.3 Automatic Classification
- On each new transaction:
  1. Check description against `classification_rules` keywords
  2. If match found → assign category and set `transaction_type = "variable_expense"`
  3. Check against `fixed_expenses` keywords → if match, set `transaction_type = "fixed_expense"`
  4. Check against `fixed_incomes` → if match, set `transaction_type = "income"`
  5. If no match → leave as uncategorized

### 3.4 Manual Classification
- API to manually assign a category to a transaction
- Option to create a new classification rule from a manual assignment
  - e.g., user classifies "Café Joe" as "Food" → auto-create rule: keyword="Café Joe", category="Food"

### 3.5 Installment Handling
- Track installment transactions (installment_number, installment_total)
- Calculate remaining installment amount for budget forecasting

### 3.6 Balance Snapshot Tracking
- Store account balance snapshots from each scraper run (date, account_id, balance)
- Use snapshots to calculate opening/closing balance for monthly view
- If no snapshot exists for month start, interpolate from nearest available snapshot

---

## 4. API Layer

### 4.1 Framework Setup
- Python web framework: FastAPI or Flask
- RESTful API endpoints
- JSON responses

### 4.2 Endpoints — Overview (Screen 1)
- `GET /api/overview`
  - Total balance across all accounts
  - Balance per account
  - Remaining monthly budget
  - Savings list with current amounts

### 4.3 Endpoints — Monthly View (Screen 2)
- `GET /api/monthly?month=2026-02&account_id=all`
  - Opening and closing balance
  - Income breakdown
  - Fixed expenses breakdown (with paid/expected status)
  - Savings deposits
  - Variable expenses by category (with budget vs. actual)
  - Uncategorized transactions
  - End-of-month forecast
- `GET /api/monthly/trends?month=2026-02`
  - Per-category comparison vs. 3/6 month average
  - Overall expense trend (up/down + percentage)
  - Previous month comparison
  - Budget compliance summary

### 4.4 Endpoints — Yearly View (Screen 3)
- `GET /api/yearly?year=2026`
  - Monthly table: income, expenses, balance per month
  - Annual totals
- `GET /api/yearly/trends?year=2026`
  - Annual trend direction
  - Most expensive months
  - Year-over-year comparison
  - Monthly averages
  - Fastest growing categories

### 4.5 Endpoints — Settings (Screen 4)
- **Accounts:** `GET/POST/PUT/DELETE /api/accounts`
- **Credit Cards:** `GET/POST/PUT/DELETE /api/credit-cards`
- **Fixed Income:** `GET/POST/PUT/DELETE /api/fixed-incomes`
- **Fixed Expenses:** `GET/POST/PUT/DELETE /api/fixed-expenses`
- **Categories:** `GET/POST/PUT/DELETE /api/categories`
- **Classification Rules:** `GET/POST/PUT/DELETE /api/classification-rules`
- **Savings:** `GET/POST/PUT/DELETE /api/savings`

### 4.6 Endpoints — Wedding Planner (Screen 5)
- **Vendors:** `GET/POST/PUT/DELETE /api/wedding/vendors`
- **Payments:** `GET/POST/PUT/DELETE /api/wedding/payments`
- **Settings:** `GET/PUT /api/wedding/settings` (includes guest counts and budget)
- `GET /api/wedding/summary`
  - Total cost, paid so far, remaining
  - Budget vs. actual
- `GET /api/wedding/calculator`
  - Expected income (balances + salaries + gifts + additional)
  - Expected expenses (living expenses + remaining payments + additional)
  - Projected balance before and after wedding

### 4.7 Endpoints — Transactions
- `GET /api/transactions?from=&to=&category=&account=`
  - Filtered transaction list
- `PUT /api/transactions/:id`
  - Edit a transaction (category, notes, split, correct amount)
- `PUT /api/transactions/:id/classify`
  - Manually classify a transaction
- `GET /api/transactions/uncategorized`
  - List of unclassified transactions

---

## 5. Business Logic & Calculations

### 5.1 End-of-Month Forecast
- Current balance
- Plus: expected income not yet received (based on fixed_incomes + day_of_month)
- Minus: expected fixed expenses not yet charged
- Minus: estimated remaining variable expenses (based on average daily spending × remaining days)

### 5.2 Trend Calculations
- Monthly average per category (rolling 3 and 6 months)
- Month-over-month change (amount and percentage)
- Year-over-year comparison
- Expense direction indicator (up/down/stable)

### 5.3 Budget Tracking
- Per category: budget defined vs. actual spent
- Overall: total budget vs. total spent
- Percentage used and remaining

### 5.4 Unusual Expense Detection
- Flag transactions significantly above the average for their category
- Threshold: e.g., more than 2× the average transaction in that category

### 5.5 Credit Card Billing Day Logic
- Determine if a credit card transaction is "charged" or "expected" based on the card's billing day
- Transactions made before the billing day → charged this month
- Transactions made after the billing day → expected next month
- Use this logic in Monthly View to separate charged vs. expected expenses
- Factor billing day into end-of-month forecast calculations

### 5.6 Savings Current Value Tracking
- Determine how savings current values are updated:
  - Option A: Scrape from bank (if savings appear in scraper data)
  - Option B: Manual update via Settings
- Track value changes over time for the Overview screen

### 5.7 Wedding Calculator
- Pull current account balances
- Calculate months until wedding
- Project income: (months × monthly income) + estimated gifts + additional
- Project expenses: (months × monthly expenses) + remaining vendor payments + additional
- Result: projected balance before and after wedding with status indicator

---

## 6. Project Structure

```
cashboard/
├── .env                          # Credentials (not in git)
├── .gitignore
├── config.py                     # App-level config (DB path, thresholds, schedule intervals)
├── requirements.txt              # Python dependencies
├── README.md
│
├── db/
│   ├── database.py               # DB connection and initialization
│   ├── schema.sql                # Table creation SQL
│   └── migrations/               # Schema version changes
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
│   ├── app.py                     # FastAPI/Flask app entry point
│   ├── routes/
│   │   ├── overview.py
│   │   ├── monthly.py
│   │   ├── yearly.py
│   │   ├── settings.py
│   │   ├── transactions.py
│   │   └── wedding.py
│   └── models/
│       └── schemas.py             # Request/response models
│
├── services/
│   ├── forecast.py                # End-of-month forecasting
│   ├── trends.py                  # Trend calculations
│   ├── budget.py                  # Budget tracking logic
│   ├── anomaly.py                 # Unusual expense detection
│   └── wedding_calculator.py      # Wedding financial projections
│
└── scripts/
    ├── run_scrapers.py            # Trigger scraper + ingestion
    └── setup_db.py                # First-time DB setup
```

---

## 7. Implementation Order

### Phase 1 — Foundation
1. Database setup (tables, indexes, seed data)
2. Settings CRUD (accounts, credit cards with billing day, categories, fixed income/expenses, savings)

### Phase 2 — Scraper & Data Import
3. Node.js scraper script (with error handling & retry)
4. Python ingestion pipeline (JSON → DB + balance snapshots)
5. Duplicate detection
6. Automatic classification
7. Credit card billing day logic (charged vs. expected)
8. Manual CSV import (uses same ingestion pipeline)
9. Scraper scheduling

### Phase 3 — Core Features
10. Overview endpoint (balances from snapshots, savings, budget remaining)
11. Monthly view endpoint + calculations (opening/closing balance, charged/expected)
12. Budget tracking
13. End-of-month forecasting
14. Trend calculations

### Phase 4 — Yearly & Advanced
15. Yearly view endpoint
16. Unusual expense detection
17. Year-over-year comparisons

### Phase 5 — Wedding
18. Wedding vendors & payments CRUD
19. Wedding settings (guest counts, budget, calculator inputs)
20. Wedding calculator

### Phase 6 — Frontend
21. Build the UI on top of the API
