from pydantic import BaseModel
from typing import Optional


# --- Accounts ---

class AccountCreate(BaseModel):
    name: str
    bank: str
    type: str  # 'personal' | 'shared'
    scraper_type: Optional[str] = None


class AccountResponse(AccountCreate):
    id: int


# --- Credit Cards ---

class CreditCardCreate(BaseModel):
    account_id: int
    name: str
    company: str
    last_4_digits: Optional[str] = None
    billing_day: Optional[int] = None
    scraper_type: Optional[str] = None


class CreditCardResponse(CreditCardCreate):
    id: int


# --- Categories ---

class CategoryCreate(BaseModel):
    name: str
    monthly_budget: Optional[float] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(CategoryCreate):
    id: int


# --- Classification Rules ---

class ClassificationRuleCreate(BaseModel):
    category_id: int
    keyword: str
    match_type: str = "contains"  # 'contains' | 'exact' | 'starts_with'


class ClassificationRuleResponse(ClassificationRuleCreate):
    id: int


# --- Fixed Incomes ---

class FixedIncomeCreate(BaseModel):
    name: str
    expected_amount: float
    frequency: str = "monthly"  # 'monthly' | 'weekly' | 'biweekly'
    account_id: Optional[int] = None
    day_of_month: Optional[int] = None
    keyword: Optional[str] = None


class FixedIncomeResponse(FixedIncomeCreate):
    id: int


# --- Fixed Expenses ---

class FixedExpenseCreate(BaseModel):
    name: str
    expected_amount: float
    frequency: str = "monthly"  # 'monthly' | 'bimonthly' | 'yearly'
    payment_method: Optional[str] = None  # 'credit_card' | 'standing_order' | 'direct_debit'
    credit_card_id: Optional[int] = None
    account_id: Optional[int] = None
    keyword: Optional[str] = None
    day_of_month: Optional[int] = None


class FixedExpenseResponse(FixedExpenseCreate):
    id: int


# --- Savings ---

class SavingsCreate(BaseModel):
    name: str
    account_id: Optional[int] = None
    initial_amount: Optional[float] = None
    current_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    interest_rate: Optional[float] = None


class SavingsResponse(SavingsCreate):
    id: int
