PRAGMA foreign_keys = ON;

-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 1. Bank Accounts
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bank TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('personal', 'shared')),
    scraper_type TEXT
);

-- 2. Credit Cards
CREATE TABLE IF NOT EXISTS credit_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    last_4_digits TEXT,
    billing_day INTEGER,
    scraper_type TEXT
);

-- 3. Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK (source_type IN ('bank', 'credit_card')),
    source_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    processed_date TEXT,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'ILS',
    description TEXT,
    category_id INTEGER REFERENCES categories(id),
    transaction_type TEXT CHECK (transaction_type IN ('income', 'fixed_expense', 'variable_expense', 'saving')),
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'pending')),
    installment_number INTEGER,
    installment_total INTEGER,
    original_id TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 4. Categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    monthly_budget REAL,
    icon TEXT,
    color TEXT
);

-- 5. Classification Rules
CREATE TABLE IF NOT EXISTS classification_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    keyword TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'contains' CHECK (match_type IN ('contains', 'exact', 'starts_with'))
);

-- 6. Fixed Incomes
CREATE TABLE IF NOT EXISTS fixed_incomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    expected_amount REAL NOT NULL,
    frequency TEXT NOT NULL DEFAULT 'monthly' CHECK (frequency IN ('monthly', 'weekly', 'biweekly')),
    account_id INTEGER REFERENCES accounts(id),
    day_of_month INTEGER,
    keyword TEXT
);

-- 7. Fixed Expenses
CREATE TABLE IF NOT EXISTS fixed_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    expected_amount REAL NOT NULL,
    frequency TEXT NOT NULL DEFAULT 'monthly' CHECK (frequency IN ('monthly', 'bimonthly', 'yearly')),
    payment_method TEXT CHECK (payment_method IN ('credit_card', 'standing_order', 'direct_debit')),
    credit_card_id INTEGER REFERENCES credit_cards(id),
    account_id INTEGER REFERENCES accounts(id),
    keyword TEXT,
    day_of_month INTEGER
);

-- 8. Savings
CREATE TABLE IF NOT EXISTS savings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account_id INTEGER REFERENCES accounts(id),
    initial_amount REAL,
    current_amount REAL,
    start_date TEXT,
    end_date TEXT,
    interest_rate REAL
);

-- 9. Wedding Vendors
CREATE TABLE IF NOT EXISTS wedding_vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    total_cost REAL,
    notes TEXT
);

-- 10. Wedding Payments
CREATE TABLE IF NOT EXISTS wedding_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES wedding_vendors(id),
    payment_type TEXT CHECK (payment_type IN ('advance', 'interim', 'final')),
    amount REAL NOT NULL,
    due_date TEXT,
    is_paid INTEGER NOT NULL DEFAULT 0,
    paid_date TEXT
);

-- 11. Wedding Settings
CREATE TABLE IF NOT EXISTS wedding_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    wedding_date TEXT,
    original_budget REAL,
    total_invited INTEGER,
    confirmed_count INTEGER,
    declined_count INTEGER,
    avg_gift_estimate REAL,
    additional_income REAL,
    additional_expenses REAL
);

-- 12. Balance Snapshots
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    date TEXT NOT NULL,
    balance REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 13. Scrape Log
CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK (source_type IN ('bank', 'credit_card')),
    source_id INTEGER NOT NULL,
    scraped_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    transactions_count INTEGER,
    error_message TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_source_id ON transactions(source_id);
CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_original_id ON transactions(original_id);
CREATE INDEX IF NOT EXISTS idx_balance_snapshots_date ON balance_snapshots(date);
