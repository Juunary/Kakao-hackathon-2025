"""
database.py — SQLAlchemy models + DB initialisation/seed.

SECURITY BOUNDARY:
  Exports: init_db, create_session, get_db, User, Account, Transaction.
  The engine and SessionLocal are intentionally NOT exported.
  Agent/LLM code must never import engine or SessionLocal.
  All DB access must go through the tool layer only.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Generator

from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

# ---------------------------------------------------------------------------
# Engine — private to this module
# ---------------------------------------------------------------------------
_DATABASE_URL = "sqlite:///./dev.db"
_engine = create_engine(_DATABASE_URL, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# ORM base & models
# ---------------------------------------------------------------------------
class _Base(DeclarativeBase):
    pass


class User(_Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Account(_Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    balance_krw: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Transaction(_Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(String, nullable=False)  # "debit" | "credit"
    amount_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    counterparty_masked: Mapped[str] = mapped_column(String, nullable=False)
    memo: Mapped[str] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@contextmanager
def create_session() -> Generator[Session, None, None]:
    """
    Context manager for a DB session.
    Intended for the TOOL LAYER only — never use in agent/LLM code.

    Usage:
        with create_session() as db:
            ...
    """
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection style generator.
    Intended for the TOOL LAYER only.
    """
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create tables and seed dev data (idempotent)."""
    _Base.metadata.create_all(bind=_engine)
    _seed_dev_data()


def _seed_dev_data() -> None:
    now = datetime.now(timezone.utc)
    with create_session() as db:
        # Seed user + account if not present
        if not db.get(User, "u_001"):
            db.add(User(user_id="u_001", display_name="홍길동", created_at=now))
            db.add(
                Account(
                    account_id="acc_001",
                    user_id="u_001",
                    balance_krw=1_250_000,
                    updated_at=now,
                )
            )

        # Seed transactions independently (handles upgrade from Phase 1 DB)
        if not db.get(Transaction, "t_001"):
            _txns = [
                ("t_001", "credit", 2_000_000, "급여", "3월 급여", 7),
                ("t_002", "debit",     12_000, "스타벅스", "아메리카노", 6),
                ("t_003", "debit",     55_000, "쿠팡", "생필품", 5),
                ("t_004", "debit",    150_000, "한전", "전기요금", 4),
                ("t_005", "credit",   500_000, "환급", "세금 환급", 3),
            ]
            for tid, ttype, amount, counterparty, memo, days_ago in _txns:
                db.add(
                    Transaction(
                        transaction_id=tid,
                        user_id="u_001",
                        timestamp=now - timedelta(days=days_ago),
                        type=ttype,
                        amount_krw=amount,
                        counterparty_masked=counterparty,
                        memo=memo,
                    )
                )
