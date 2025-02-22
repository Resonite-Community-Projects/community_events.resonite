import contextlib
from datetime import timedelta, date

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from resonite_communities.auth.users import current_active_user, User
from resonite_communities.auth.db import get_async_session
from resonite_communities.clients.web.models.metrics import Metrics
from resonite_communities.clients.web.utils.templates import templates


router = APIRouter()

@router.get("/admin/metrics")
async def get_metrics(request: Request, user: User = Depends(current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    get_async_session_context = contextlib.asynccontextmanager(get_async_session)

    async with get_async_session_context() as session:
        results = await session.execute(select(Metrics))
        metrics = results.scalars().all()

        # Prepare data for charts
        labels = [metric.endpoint for metric in metrics]
        data = [1 for _ in metrics]  # Simplified for example purposes

        # Prepare data for daily users
        today = date.today()
        start_date = today - timedelta(days=7)
        daily_unique_users_result = await session.execute(
            select(
                func.date(Metrics.timestamp).label('date'),
                func.count(func.distinct(Metrics.hashed_ip)).label('count')
            ).where(
                func.date(Metrics.timestamp) >= start_date
            ).group_by(func.date(Metrics.timestamp))
        )
        daily_unique_users = {str(date): count for date, count in daily_unique_users_result.all()}

        # Convert keys and values to lists
        daily_unique_users_labels = list(daily_unique_users.keys())
        daily_unique_users_data = list(daily_unique_users.values())

        # Calculate average and last day's unique user count
        total_unique_users = sum(daily_unique_users.values())
        average_unique_users = total_unique_users / len(daily_unique_users) if daily_unique_users else 0
        last_day_unique_users = daily_unique_users.get(str(today), 0)


        country_data_result = await session.execute(
            select(
                Metrics.country,
                func.count(func.distinct(Metrics.hashed_ip)).label('count')
            ).where(
                func.date(Metrics.timestamp) == today
            ).group_by(Metrics.country)
        )
        country_data = [{"name": country, "value": count} for country, count in country_data_result.all()]
        max_users = max([count for _, count in country_data], default=0)

    return templates.TemplateResponse("admin_metrics.html", {
        "request": request,
        "metrics": metrics,
        "daily_unique_users_labels": daily_unique_users_labels,
        "daily_unique_users_data": daily_unique_users_data,
        "average_unique_users": average_unique_users,
        "last_day_unique_users": last_day_unique_users,
        "country_data": country_data,
        "max_users": max_users
    })