"""Query counts for N+1 documentation (PERFORMANCE.md)."""
from __future__ import annotations

from datetime import date, timedelta

from app import db
from app.models import Category, Transaction, User
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import joinedload


def _count_queries(engine: Engine):
    counts = {"n": 0}

    def _before(*_args, **_kwargs):
        counts["n"] += 1

    event.listen(engine, "before_cursor_execute", _before)
    return counts, lambda: event.remove(engine, "before_cursor_execute", _before)


def _seed_tx_with_category(uid: int, cat: Category, n: int = 5) -> None:
    for i in range(n):
        db.session.add(
            Transaction(
                user_id=uid,
                date=date.today() - timedelta(days=i),
                amount=10,
                type="expense",
                category_id=cat.id,
            )
        )
    db.session.commit()


def test_joinedload_emits_no_more_queries_than_lazy(app):
    """Eager category load should not increase statement count vs lazy (often fewer)."""
    with app.app_context():
        u = User.query.first()
        uid = u.id
        c = Category(user_id=uid, name="PerfCat", type="expense")
        db.session.add(c)
        db.session.commit()
        _seed_tx_with_category(uid, c, n=8)

        engine = db.engine

        counts_lazy, done_lazy = _count_queries(engine)
        try:
            rows = (
                Transaction.query.filter_by(user_id=uid).order_by(Transaction.date.desc()).limit(200).all()
            )
            for t in rows:
                _ = t.category.name if t.category else None
        finally:
            done_lazy()
        lazy_n = counts_lazy["n"]

        counts_eager, done_eager = _count_queries(engine)
        try:
            rows2 = (
                Transaction.query.options(joinedload(Transaction.category))
                .filter_by(user_id=uid)
                .order_by(Transaction.date.desc())
                .limit(200)
                .all()
            )
            for t in rows2:
                _ = t.category.name if t.category else None
        finally:
            done_eager()
        eager_n = counts_eager["n"]

        assert eager_n <= lazy_n
