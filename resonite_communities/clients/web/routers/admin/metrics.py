import calendar
import contextlib
from copy import deepcopy
from datetime import timedelta, date

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from sqlalchemy import func, select, extract
from resonite_communities.auth.db import get_async_session
from resonite_communities.clients.models.metrics import Metrics
from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session

Config = ConfigManager(get_session).config

router = APIRouter()

@router.get("/admin/metrics")
async def get_metrics(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    today = date.today()
    yesterday = today - timedelta(days=1)
    past_week = today - timedelta(days=7)

    get_async_session_context = contextlib.asynccontextmanager(get_async_session)

    async with get_async_session_context() as session:
        results = await session.execute(select(Metrics))
        metrics = results.scalars().all()

        metrics_domains_result = (
            await session.execute(
                select(
                    Metrics.domain, Metrics.endpoint, func.count()
                ).where(
                    func.date(Metrics.timestamp) >= past_week
                ).group_by(
                    Metrics.domain, Metrics.endpoint
                )
            )
        ).all()

        _metrics_domains = {}
        for metrics_domain in metrics_domains_result:
            if metrics_domain[0] not in _metrics_domains:
                _metrics_domains[metrics_domain[0]] = {}
                _metrics_domains[metrics_domain[0]]["counts"] = []
                _metrics_domains[metrics_domain[0]]["total_counts"] = 0
            _metrics_domains[metrics_domain[0]]["counts"].append({
                "endpoint": metrics_domain[1],
                "count": metrics_domain[2]
            })
            _metrics_domains[metrics_domain[0]]["total_counts"] += metrics_domain[2]

        metrics_domains = {}

        for monitored_url in Config.MONITORED_DOMAINS:
            if monitored_url['url'] in _metrics_domains:
                metrics_domains[monitored_url['url']] = _metrics_domains[monitored_url['url']]

        versions_result = (
            await session.execute(
                select(Metrics.version, func.count())
                .group_by(Metrics.version)
            )
        ).all()

        versions = []
        for version in versions_result:
            versions.append({
                "version": version[0],
                "count": version[1]
            })

        daily_unique_users_result = await session.execute(
            select(
                func.date(Metrics.timestamp).label('date'),
                func.count(func.distinct(Metrics.hashed_ip)).label('count')
            ).where(
                func.date(Metrics.timestamp) >= past_week
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

        # Get data for day of week / hour of day heatmap for the past 30 days
        past_month = today - timedelta(days=30)
        hourly_activity_result = await session.execute(
            select(
                extract('dow', Metrics.timestamp).label('day_of_week'),
                extract('hour', Metrics.timestamp).label('hour_of_day'),
                func.count(func.distinct(Metrics.hashed_ip)).label('users')
            ).where(
                func.date(Metrics.timestamp) >= past_month
            ).group_by(
                extract('dow', Metrics.timestamp),
                extract('hour', Metrics.timestamp)
            )
        )

        # Initialize empty heatmap data with zeros
        days_of_week = 7
        hours_of_day = 24
        heatmap_data = [[0 for _ in range(hours_of_day)] for _ in range(days_of_week)]

        # Fill in the heatmap with actual data
        for day, hour, count in hourly_activity_result.all():
            # Convert to integer (day is 0-6, where 0 is Sunday)
            day_idx = int(day)
            hour_idx = int(hour)
            heatmap_data[day_idx][hour_idx] = count

        # Prepare day and hour labels for the heatmap
        day_labels = [calendar.day_name[i] for i in range(7)]  # Sunday to Saturday
        hour_labels = [f"{i:02d}:00" for i in range(24)]

        country_data_result = await session.execute(
            select(
                Metrics.country,
                func.count(func.distinct(Metrics.hashed_ip)).label('count')
            ).where(
                func.date(Metrics.timestamp) == yesterday
            ).group_by(Metrics.country)
        )
        country_data = [{"name": country, "value": count} for country, count in country_data_result.all()]
        max_users = max([count for _, count in country_data], default=0)

    return templates.TemplateResponse("admin/metrics.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "request": request,
        "metrics_domains": metrics_domains,
        "versions": versions,
        "daily_unique_users_labels": daily_unique_users_labels,
        "daily_unique_users_data": daily_unique_users_data,
        "average_unique_users": average_unique_users,
        "last_day_unique_users": last_day_unique_users,
        "country_data": country_data,
        "max_users": max_users,
        "heatmap_data": heatmap_data,
        "day_labels": day_labels,
        "hour_labels": hour_labels,
    })