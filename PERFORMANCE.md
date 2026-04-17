# Query performance (N+1 audit)

## Method

We count SQL statements issued during a request using `sqlalchemy.event.listens_for(Engine, "before_cursor_execute")` (see `tests/test_performance_queries.py`).

## Transactions list (`GET /transactions/`)

**Before:** Loading transactions then accessing `transaction.category` may issue additional queries (lazy load), depending on dialect and SQLAlchemy version.

**After:** `joinedload(Transaction.category)` loads categories eagerly so the list view does not pay per-row lazy loads.

We assert in tests that the eager path uses **no more** SQL statements than the lazy path (`tests/test_performance_queries.py`).

## Dashboard (`GET /dashboard`)

Category breakdown uses a single aggregated `JOIN` + `GROUP BY` in `get_category_breakdown()` — no per-row ORM access on transactions. No N+1 observed.

## How to re-measure

```bash
python -m pytest tests/test_performance_queries.py -v
```
