from fastapi import APIRouter

from app.api.v1.endpoints import (
    account,
    auth,
    budget,
    category,
    chat,
    connect,
    export,
    notification,
    portfolio,
    report,
    transaction,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(account.router, prefix="/accounts", tags=["Accounts"])
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(transaction.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(report.router, prefix="/reports", tags=["Reports"])
api_router.include_router(connect.router, prefix="/connect", tags=["Connect"])
api_router.include_router(export.router, prefix="/exports", tags=["Exports"])
api_router.include_router(notification.router, prefix="/notifications", tags=["Notifications"])
