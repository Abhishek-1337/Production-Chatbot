from datetime import datetime, timezone, timedelta, date
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.user import User
from models.token_usage import TokenUsage
from services.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _parse_date(value: str | None, default: date | None = None) -> datetime | None:
    if value is None:
        return None
    try:
        # accept YYYY-MM-DD
        d = datetime.fromisoformat(value)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}, use YYYY-MM-DD")


@router.get("/token-usage/daily")
async def daily_usage(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
    source: Literal["all", "llm", "embedding", "summary"] = Query("all"),
):
    # default last 30 days
    now = datetime.now(timezone.utc).date()
    if start is None:
        start_dt = datetime.combine(now - timedelta(days=29), datetime.min.time(), tzinfo=timezone.utc)
    else:
        start_dt = _parse_date(start)
        start_dt = datetime.combine(start_dt.date(), datetime.min.time(), tzinfo=timezone.utc)
    if end is None:
        end_dt = datetime.combine(now, datetime.max.time(), tzinfo=timezone.utc)
    else:
        end_dt = _parse_date(end)
        end_dt = datetime.combine(end_dt.date(), datetime.max.time(), tzinfo=timezone.utc)

    conditions = [TokenUsage.created_at >= start_dt, TokenUsage.created_at <= end_dt]
    if source != "all":
        conditions.append(TokenUsage.source == source)

    # group by day trunc UTC
    day_col = func.date_trunc("day", TokenUsage.created_at).label("day")
    stmt = (
        select(
            day_col,
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
            func.count(TokenUsage.id).label("query_count"),
        )
        .where(and_(*conditions))
        .group_by(day_col)
        .order_by(day_col)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # fill missing days for continuous chart
    data_by_day = {r.day.date().isoformat(): r for r in rows}
    out = []
    cur = start_dt.date()
    end_date = end_dt.date()
    while cur <= end_date:
        key = cur.isoformat()
        r = data_by_day.get(key)
        if r:
            out.append({
                "date": key,
                "total_tokens": int(r.total_tokens or 0),
                "prompt_tokens": int(r.prompt_tokens or 0),
                "completion_tokens": int(r.completion_tokens or 0),
                "query_count": int(r.query_count or 0),
            })
        else:
            out.append({"date": key, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "query_count": 0})
        cur += timedelta(days=1)

    return {"data": out, "start": start_dt.date().isoformat(), "end": end_dt.date().isoformat(), "source": source}


@router.get("/token-usage/top-users")
async def top_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start: str | None = Query(None),
    end: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    source: Literal["all", "llm", "embedding", "summary"] = Query("all"),
):
    now = datetime.now(timezone.utc).date()
    if start is None:
        start_dt = datetime.combine(now - timedelta(days=29), datetime.min.time(), tzinfo=timezone.utc)
    else:
        start_dt = _parse_date(start)
        start_dt = datetime.combine(start_dt.date(), datetime.min.time(), tzinfo=timezone.utc)
    if end is None:
        end_dt = datetime.combine(now, datetime.max.time(), tzinfo=timezone.utc)
    else:
        end_dt = _parse_date(end)
        end_dt = datetime.combine(end_dt.date(), datetime.max.time(), tzinfo=timezone.utc)

    conditions = [TokenUsage.created_at >= start_dt, TokenUsage.created_at <= end_dt]
    if source != "all":
        conditions.append(TokenUsage.source == source)

    stmt = (
        select(
            TokenUsage.user_id,
            User.email,
            User.name,
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
            func.count(TokenUsage.id).label("query_count"),
        )
        .join(User, User.id == TokenUsage.user_id)
        .where(and_(*conditions))
        .group_by(TokenUsage.user_id, User.email, User.name)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    data = [
        {
            "user_id": str(r.user_id),
            "email": r.email,
            "name": r.name,
            "total_tokens": int(r.total_tokens or 0),
            "prompt_tokens": int(r.prompt_tokens or 0),
            "completion_tokens": int(r.completion_tokens or 0),
            "query_count": int(r.query_count or 0),
        }
        for r in rows
    ]
    return {"data": data, "start": start_dt.date().isoformat(), "end": end_dt.date().isoformat(), "source": source}


@router.get("/token-usage/summary")
async def summary(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    source: Literal["all", "llm", "embedding", "summary"] = Query("all"),
):
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=6)
    month_start = today_start - timedelta(days=29)

    async def _sum_since(since: datetime):
        conditions = [TokenUsage.created_at >= since]
        if source != "all":
            conditions.append(TokenUsage.source == source)
        stmt = select(func.coalesce(func.sum(TokenUsage.total_tokens), 0)).where(and_(*conditions))
        res = await db.execute(stmt)
        return int(res.scalar() or 0)

    total = await _sum_since(datetime(1970, 1, 1, tzinfo=timezone.utc))
    today = await _sum_since(today_start)
    week = await _sum_since(week_start)
    month = await _sum_since(month_start)

    # distinct users in last 30 days
    stmt_users = select(func.count(func.distinct(TokenUsage.user_id))).where(TokenUsage.created_at >= month_start)
    if source != "all":
        stmt_users = stmt_users.where(TokenUsage.source == source)
    res = await db.execute(stmt_users)
    active_users = int(res.scalar() or 0)

    return {
        "total_tokens": total,
        "today_tokens": today,
        "last_7d_tokens": week,
        "last_30d_tokens": month,
        "active_users_30d": active_users,
        "source": source,
    }


@router.get("/token-usage/top-per-day")
async def top_per_day(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start: str | None = Query(None),
    end: str | None = Query(None),
    source: Literal["all", "llm", "embedding", "summary"] = Query("all"),
):
    """For each day, who consumed most tokens."""
    now = datetime.now(timezone.utc).date()
    if start is None:
        start_dt = datetime.combine(now - timedelta(days=29), datetime.min.time(), tzinfo=timezone.utc)
    else:
        start_dt = _parse_date(start)
        start_dt = datetime.combine(start_dt.date(), datetime.min.time(), tzinfo=timezone.utc)
    if end is None:
        end_dt = datetime.combine(now, datetime.max.time(), tzinfo=timezone.utc)
    else:
        end_dt = _parse_date(end)
        end_dt = datetime.combine(end_dt.date(), datetime.max.time(), tzinfo=timezone.utc)

    conditions = [TokenUsage.created_at >= start_dt, TokenUsage.created_at <= end_dt]
    if source != "all":
        conditions.append(TokenUsage.source == source)

    day_col = func.date_trunc("day", TokenUsage.created_at).label("day")
    # subquery sum per day per user
    sub = (
        select(
            day_col.label("day"),
            TokenUsage.user_id.label("user_id"),
            func.sum(TokenUsage.total_tokens).label("total"),
        )
        .where(and_(*conditions))
        .group_by(day_col, TokenUsage.user_id)
        .subquery()
    )
    # rank per day
    from sqlalchemy import func as sa_func
    # Use DISTINCT ON approach for postgres: select max per day
    # Simpler: fetch all and compute max in python
    stmt = select(sub.c.day, sub.c.user_id, sub.c.total)
    result = await db.execute(stmt)
    rows = result.all()
    # group by day
    from collections import defaultdict
    by_day = defaultdict(list)
    for r in rows:
        by_day[r.day.date().isoformat()].append((r.user_id, r.total))
    # fetch user emails
    user_ids = {uid for lst in by_day.values() for uid, _ in lst}
    email_map = {}
    if user_ids:
        res = await db.execute(select(User.id, User.email, User.name).where(User.id.in_(list(user_ids))))
        for uid, email, name in res.all():
            email_map[uid] = (email, name)
    out = []
    cur = start_dt.date()
    end_date = end_dt.date()
    while cur <= end_date:
        key = cur.isoformat()
        lst = by_day.get(key, [])
        if lst:
            top_uid, top_total = max(lst, key=lambda x: x[1])
            email, name = email_map.get(top_uid, ("unknown", "unknown"))
            out.append({"date": key, "user_id": str(top_uid), "email": email, "name": name, "total_tokens": int(top_total)})
        else:
            out.append({"date": key, "user_id": None, "email": None, "name": None, "total_tokens": 0})
        cur += timedelta(days=1)
    return {"data": out}
