from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db
from api.routes import (
    accounts,
    credit_cards,
    categories,
    classification_rules,
    fixed_incomes,
    fixed_expenses,
    savings,
)

app = FastAPI(title="Cashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(accounts.router)
app.include_router(credit_cards.router)
app.include_router(categories.router)
app.include_router(classification_rules.router)
app.include_router(fixed_incomes.router)
app.include_router(fixed_expenses.router)
app.include_router(savings.router)
