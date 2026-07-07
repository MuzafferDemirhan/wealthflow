import uuid
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account import Account
from app.models.budget import Budget
from app.models.chat_message import ChatMessage
from app.models.holding import Holding
from app.models.transaction import Transaction, TransactionStatus

SYSTEM_PROMPT = """You are WealthFlow AI, a helpful financial advisor assistant. \
You help users understand their spending, budgets, investments, and overall financial health. \
You have access to the user's financial data which is provided in the context below. \
Be concise, friendly, and data-driven. When discussing amounts, include the currency. \
If you don't know something or the data doesn't support an answer, say so honestly. \
Do not provide specific investment advice - instead help users understand their portfolio composition and performance."""


def _build_context(db: Session, user_id: uuid.UUID) -> str:
    lines = []

    account_balances = (
        db.execute(
            select(Account).where(
                Account.user_id == user_id,
                Account.is_active,
            )
        )
        .scalars()
        .all()
    )
    if account_balances:
        lines.append("=== ACCOUNTS ===")
        for acc in account_balances:
            lines.append(
                f"{acc.display_name} ({acc.account_type.value}): "
                f"{acc.currency} {acc.current_balance or 0:,.2f}"
            )
        total = sum(
            (acc.current_balance or 0) for acc in account_balances
        )
        lines.append(f"Total balance: {account_balances[0].currency} {total:,.2f}")

    thirty_days_ago = date.today() - timedelta(days=30)
    recent_txns = (
        db.execute(
            select(Transaction)
            .where(
                Transaction.account_id.in_(
                    select(Account.id).where(
                        Account.user_id == user_id,
                        Account.is_active,
                    )
                ),
                Transaction.booking_date >= thirty_days_ago,
            )
            .order_by(Transaction.booking_date.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    if recent_txns:
        lines.append("=== RECENT TRANSACTIONS (last 30 days) ===")
        for txn in recent_txns:
            lines.append(
                f"{txn.booking_date} | {txn.description[:50]:50s} | "
                f"{txn.currency} {abs(txn.amount):>10,.2f} "
                f"({'income' if txn.amount >= 0 else 'expense'})"
            )

    budgets = (
        db.execute(
            select(Budget).where(
                Budget.user_id == user_id,
            )
        )
        .scalars()
        .all()
    )
    if budgets:
        lines.append("=== BUDGETS ===")
        for b in budgets:
            lines.append(
                f"Category: {b.category.name if b.category else 'Unknown'} | "
                f"Limit: {b.currency} {b.amount_limit:,.2f} | "
                f"Spent: {b.currency} {b.spent:,.2f} ({b.progress_pct:.0f}%)"
            )

    holdings = (
        db.execute(
            select(Holding).where(Holding.user_id == user_id)
        )
        .scalars()
        .all()
    )
    if holdings:
        lines.append("=== PORTFOLIO ===")
        for h in holdings:
            mv = h.market_value
            lines.append(
                f"{h.symbol} ({h.name}): {h.quantity} shares @ "
                f"{h.currency} {h.current_price or 0:,.2f} = "
                f"{h.currency} {mv or 0:,.2f}"
            )

    return "\n".join(lines) if lines else "No financial data available yet."


def process_message(
    db: Session,
    user_id: uuid.UUID,
    message: str,
    conversation_id: uuid.UUID,
) -> ChatMessage:
    user_msg = ChatMessage(
        user_id=user_id,
        conversation_id=conversation_id,
        role="user",
        content=message,
    )
    db.add(user_msg)
    db.flush()

    history = (
        db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.user_id == user_id,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        .scalars()
        .all()
    )

    ollama_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _build_context(db, user_id)},
    ]
    for msg in history:
        ollama_messages.append({"role": msg.role, "content": msg.content})

    reply_content = _call_ollama(ollama_messages)

    assistant_msg = ChatMessage(
        user_id=user_id,
        conversation_id=conversation_id,
        role="assistant",
        content=reply_content,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg


def _call_ollama(messages: list[dict]) -> str:
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except httpx.ConnectError:
        return "I'm sorry, but the AI service is currently unavailable. Please try again later or contact support if the issue persists."
    except httpx.TimeoutException:
        return "I'm sorry, the request timed out. Please try asking a simpler question or try again."
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = e.response.text[:200]
        return f"The AI service returned an error: {detail or e.response.status_code}"
    except Exception:
        return "I encountered an error processing your request. Please try again."


def get_history(
    db: Session,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    limit: int = 50,
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_conversations(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = (
        select(ChatMessage.conversation_id)
        .where(ChatMessage.user_id == user_id)
        .distinct()
        .order_by(ChatMessage.conversation_id)
    )
    return list(db.execute(stmt).scalars().all())


def delete_conversation(
    db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> None:
    stmt = select(ChatMessage).where(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.user_id == user_id,
    )
    messages = list(db.execute(stmt).scalars().all())
    for msg in messages:
        db.delete(msg)
    db.commit()
