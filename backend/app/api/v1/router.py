from fastapi import APIRouter

from app.api.v1.endpoints import (
    account,
    auth,
    budget,
    category,
    connect,
    portfolio,
    report,
    transaction,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(account.router, prefix="/account", tags=["Accounts"])
api_router.include_router(category.router, prefix="/category", tags=["Categories"])
api_router.include_router(transaction.router, prefix="/transaction", tags=["Transactions"])
api_router.include_router(budget.router, prefix="/budget", tags=["Budgets"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(report.router, prefix="/report", tags=["Reports"])
api_router.include_router(connect.router, prefix="/connect", tags=["Connect"])
