# Database Schema (SQLite)

## Tables

### 1. accounts — Bank Accounts
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Account name (e.g., "Leumi Shared") |
| bank | TEXT | Bank name |
| type | TEXT | "personal" / "shared" |
| scraper_type | TEXT | Scraper type (e.g., "leumi"), NULL if none |

### 2. credit_cards — Credit Cards
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| account_id | INTEGER FK → accounts | Which account it belongs to |
| name | TEXT | Card name |
| company | TEXT | Credit card company (max/isracard/cal) |
| last_4_digits | TEXT | Last 4 digits |
| billing_day | INTEGER | Day of month when charges are processed |
| scraper_type | TEXT | Scraper type |

### 3. transactions — Transactions (from all sources)
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| source_type | TEXT | "bank" / "credit_card" |
| source_id | INTEGER | Account or card ID |
| date | TEXT | Transaction date (ISO format) |
| processed_date | TEXT | Processing/charge date |
| amount | REAL | Amount (negative = expense, positive = income) |
| currency | TEXT | Currency (ILS/USD/EUR) |
| description | TEXT | Description from bank/card |
| category_id | INTEGER FK → categories | Category (NULL = uncategorized) |
| transaction_type | TEXT | "income" / "fixed_expense" / "variable_expense" / "saving" |
| status | TEXT | "completed" / "pending" |
| installment_number | INTEGER | Installment number (NULL if not installments) |
| installment_total | INTEGER | Total installments (NULL if not installments) |
| original_id | TEXT | Original ID from scraper (to prevent duplicates) |
| created_at | TEXT | When saved to DB |

### 4. categories — Variable Expense Categories
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Category name (food, transport, entertainment...) |
| monthly_budget | REAL | Monthly budget |
| icon | TEXT | Icon (optional) |
| color | TEXT | Color for charts |

### 5. classification_rules — Automatic Classification Rules
I'm not sure about this one - the classification may be done manually
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| category_id | INTEGER FK → categories | Which category to assign |
| keyword | TEXT | Keyword (e.g., "Shufersal") |
| match_type | TEXT | "contains" / "exact" / "starts_with" |

### 6. fixed_incomes — Fixed Income
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Income name (salary, rent...) |
| expected_amount | REAL | Expected amount |
| frequency | TEXT | "monthly" / "weekly" / "biweekly" |
| account_id | INTEGER FK → accounts | Which account it goes into |
| day_of_month | INTEGER | Day of month (NULL if not applicable) |

### 7. fixed_expenses — Fixed Expenses
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Expense name (rent, property tax...) |
| expected_amount | REAL | Expected amount |
| frequency | TEXT | "monthly" / "bimonthly" / "yearly" |
| payment_method | TEXT | "credit_card" / "standing_order" / "direct_debit" |
| credit_card_id | INTEGER FK → credit_cards | Which card (NULL if standing order) |
| account_id | INTEGER FK → accounts | Which account |
| keyword | TEXT | Keyword for automatic identification in transactions |

### 8. savings — Savings
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Saving name |
| account_id | INTEGER FK → accounts | Which account |
| initial_amount | REAL | Initial amount |
| current_amount | REAL | Current amount |
| start_date | TEXT | Open date |
| end_date | TEXT | Maturity date (NULL if open-ended) |
| interest_rate | REAL | Interest rate (if known) |

### 9. wedding_vendors — Wedding Vendors
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| name | TEXT | Vendor name |
| category | TEXT | Category (venue, photographer, DJ, dress, flowers...) |
| total_cost | REAL | Total cost |
| notes | TEXT | Notes |

### 10. wedding_payments — Wedding Vendor Payments
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| vendor_id | INTEGER FK → wedding_vendors | Which vendor |
| payment_type | TEXT | "advance" / "interim" / "final" |
| amount | REAL | Amount |
| due_date | TEXT | Payment due date |
| is_paid | BOOLEAN | Paid? |
| paid_date | TEXT | When actually paid (NULL if not paid) |

### 11. wedding_settings — Wedding Settings
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier (always 1 — single row) |
| wedding_date | TEXT | Wedding date |
| total_invited | INTEGER | Total invited |
| confirmed_count | INTEGER | Confirmed attendance |
| declined_count | INTEGER | Declined |
| avg_gift_estimate | REAL | Estimated average gift per guest |
| additional_income | REAL | Additional expected income |
| additional_expenses | REAL | Additional expected expenses |

### 12. scrape_log — Scraper Run Log
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifier |
| source_type | TEXT | "bank" / "credit_card" |
| source_id | INTEGER | Account/card ID |
| scraped_at | TEXT | When it ran |
| status | TEXT | "success" / "failed" |
| transactions_count | INTEGER | How many transactions were scraped |
| error_message | TEXT | Error message (NULL if successful) |

## Relationships

```
accounts ──1:N──> credit_cards
accounts ──1:N──> transactions (via source_type="bank")
credit_cards ──1:N──> transactions (via source_type="credit_card")
categories ──1:N──> transactions
categories ──1:N──> classification_rules
accounts ──1:N──> fixed_incomes
accounts ──1:N──> fixed_expenses
accounts ──1:N──> savings
credit_cards ──1:N──> fixed_expenses
wedding_vendors ──1:N──> wedding_payments
```
