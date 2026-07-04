import calendar
from datetime import timedelta, date, datetime, time

from sqlalchemy import and_, or_, select, func, extract
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends, HTTPException

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.models.metrics import Metrics, ClientType
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager

from resonite_communities.clients.api.routes.v2.admin import require_administrator_access

config_manager = ConfigManager()

logger = get_logger(__name__)

@router_v2.get("/admin/metrics/users-average")
async def get_admin_metrics_users_average(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_week = today - timedelta(days=7)

    session = await get_current_async_session()

    try:
        # Daily unique users (past week)
        daily_unique_users_result = await session.execute(
        select(
            func.date(Metrics.timestamp).label('date'),
            func.count(func.distinct(Metrics.hashed_ip)).label('count')
        ).where(
            and_(
                Metrics.timestamp >= datetime.combine(past_week, time.min),
                or_(
                    Metrics.client.is_(None),
                    Metrics.client.notin_([ClientType.BOT, ClientType.TOOL])
                )
            )
        ).group_by(func.date(Metrics.timestamp))
        )
        daily_unique_users = {
            str(date): count
            for date, count in daily_unique_users_result.all()
        }

        # Calculate averages
        total_unique_users = sum(daily_unique_users.values())
        average_unique_users = (
            total_unique_users / len(daily_unique_users)
            if daily_unique_users else 0
        )
        last_day_unique_users = daily_unique_users.get(str(today), 0)
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching users average metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return {
        "average_unique_users": average_unique_users,
        "last_day_unique_users": last_day_unique_users
    }

@router_v2.get("/admin/metrics/daily-users")
async def get_admin_metrics_daily_users(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_week = today - timedelta(days=7)

    session = await get_current_async_session()

    try:
        # Daily unique users (past week)
        daily_unique_users_result = await session.execute(
        select(
            func.date(Metrics.timestamp).label('date'),
            func.count(func.distinct(Metrics.hashed_ip)).label('count')
        ).where(
            and_(
                Metrics.timestamp >= datetime.combine(past_week, time.min),
                or_(
                    Metrics.client.is_(None),
                    Metrics.client.notin_([ClientType.BOT, ClientType.TOOL])
                )
            )
        ).group_by(func.date(Metrics.timestamp))
        )
        daily_unique_users = {
            str(date): count
            for date, count in daily_unique_users_result.all()
        }

        # Convert to lists for easier frontend consumption
        daily_unique_users_labels = list(daily_unique_users.keys())
        daily_unique_users_data = list(daily_unique_users.values())
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching daily users metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return {
        "daily_unique_users_labels": daily_unique_users_labels,
        "daily_unique_users_data": daily_unique_users_data
    }

@router_v2.get("/admin/metrics/client-versions")
async def get_admin_metrics_client_versions(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_month = today - timedelta(days=30)

    session = await get_current_async_session()

    try:
        # Version statistics
        versions_result = (
            await session.execute(
            select(Metrics.version, func.count())
            .where(Metrics.timestamp >= datetime.combine(past_month, time.min))
            .group_by(Metrics.version)
            )
        ).all()

        versions = [
            {"version": version[0], "count": version[1]}
            for version in versions_result
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching client versions metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return {
        "versions": versions
    }


@router_v2.get("/admin/metrics/google-map")
async def get_admin_metrics_google_map(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    yesterday = today - timedelta(days=1)

    session = await get_current_async_session()

    try:
        # Country data (yesterday)
        country_data_result = await session.execute(
        select(
            Metrics.country,
            func.count(func.distinct(Metrics.hashed_ip)).label('count')
        ).where(
            and_(
                Metrics.timestamp >= datetime.combine(yesterday, time.min),
                Metrics.timestamp < datetime.combine(today, time.min),
                or_(
                    Metrics.client.is_(None),
                    Metrics.client.notin_([ClientType.BOT, ClientType.TOOL])
                )
            )
        ).group_by(Metrics.country)
        )
        country_data = [
            {"name": country, "value": count}
            for country, count in country_data_result.all()
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching google map metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return {
        "country_data": country_data
    }

@router_v2.get("/admin/metrics/heatmap")
async def get_admin_metrics_heatmap(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_month = today - timedelta(days=30)

    session = await get_current_async_session()

    # Initialize empty heatmap data
    days_of_week = 7
    hours_of_day = 24
    heatmap_data = [[0 for _ in range(hours_of_day)] for _ in range(days_of_week)]

    try:
        # Hourly activity heatmap (past 30 days)
        hourly_activity_result = await session.execute(
        select(
            extract('dow', Metrics.timestamp).label('day_of_week'),
            extract('hour', Metrics.timestamp).label('hour_of_day'),
            func.count(func.distinct(Metrics.hashed_ip)).label('users')
        ).where(
            and_(
                Metrics.timestamp >= datetime.combine(past_month, time.min),
                or_(
                    Metrics.client.is_(None),
                    Metrics.client.notin_([ClientType.BOT, ClientType.TOOL])
                )
            )
        ).group_by(
            extract('dow', Metrics.timestamp),
            extract('hour', Metrics.timestamp)
        )
        )

        heatmap_data = [[0 for _ in range(hours_of_day)] for _ in range(days_of_week)]

        # Fill in the heatmap with actual data
        for day, hour, count in hourly_activity_result.all():
            # Convert to integer (day is 0-6, where 0 is Sunday)
            day_idx = int(day)
            hour_idx = int(hour)
            heatmap_data[day_idx][hour_idx] = count

        # Prepare labels for the heatmap
        day_labels = [calendar.day_name[i] for i in range(7)]  # Sunday to Saturday
        hour_labels = [f"{i:02d}:00" for i in range(24)]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching heatmap metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return {
        'heatmap_data': heatmap_data,
        "day_labels": day_labels,
        "hour_labels": hour_labels
    }

@router_v2.get("/admin/metrics/client-types")
async def get_admin_metrics_client_types(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_month = today - timedelta(days=30)

    session = await get_current_async_session()

    try:
        client_types_result = (
            await session.execute(
            select(Metrics.client, func.count())
            .where(Metrics.timestamp >= datetime.combine(past_month, time.min))
            .group_by(Metrics.client)
            )
        ).all()

        client_types = [
            {"client": client_type[0].value if client_type[0] else 'Unknown', "count": client_type[1]}
            for client_type in client_types_result
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching client types metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return client_types

@router_v2.get("/admin/metrics/domains")
async def get_admin_metrics_domains(user_auth: UserAuthModel = Depends(require_administrator_access)):
    today = date.today()
    past_month = today - timedelta(days=30)

    session = await get_current_async_session()

    try:
        # Metrics by domain and endpoint (past month)
        metrics_domains_result = (
            await session.execute(
            select(
                Metrics.domain, Metrics.endpoint, func.count()
            ).where(
                Metrics.timestamp >= datetime.combine(past_month, time.min)
            ).group_by(
                Metrics.domain, Metrics.endpoint
            )
            )
        ).all()

        _metrics_domains = {}
        for metrics_domain in metrics_domains_result:
            if metrics_domain[0] not in _metrics_domains:
                _metrics_domains[metrics_domain[0]] = {
                    "counts": [],
                    "total_counts": 0
                }
            _metrics_domains[metrics_domain[0]]["counts"].append({
                "endpoint": metrics_domain[1],
                "count": metrics_domain[2]
            })
            _metrics_domains[metrics_domain[0]]["total_counts"] += metrics_domain[2]

        # Filter by monitored domains
        metrics_domains = {}
        for monitored_url in config_manager.infrastructure_config.get('MONITORED_DOMAINS', []):
            if monitored_url.url in _metrics_domains:
                metrics_domains[monitored_url.url] = _metrics_domains[monitored_url.url]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching domains metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return metrics_domains
