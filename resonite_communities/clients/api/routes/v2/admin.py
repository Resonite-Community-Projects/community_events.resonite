from resonite_communities.clients.api.routes.routers import router_v2
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Request, Header
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.api.utils.auth import get_user_auth_from_header_or_cookie
from resonite_communities.models.signal import EventStatus
from resonite_communities.auth.db import User
from datetime import datetime, timedelta, date
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.models.community import CommunityPlatform, Community, events_platforms, streams_platforms
from resonite_communities.utils.tools import is_local_env
from resonite_communities.clients.api.utils.models import CommunityRequest
from pydantic import BaseModel
from resonite_communities.utils.db import get_current_async_session
from sqlalchemy import case, and_, not_, select, func, extract
import json
import calendar


from fastapi import Query
from typing import List, Optional

import requests

from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.config.models import AppConfig, MonitoredDomain, TwitchConfig
from resonite_communities.clients.models.metrics import Metrics

config_manager = ConfigManager()

class EventUpdateStatusRequest(BaseModel):
    id: str
    status: EventStatus

class UserUpdateStatusRequest(BaseModel):
    id: str
    is_superuser: bool
    is_moderator: bool

class DiscordImportRequest(BaseModel):
    id: str
    visibility: str

class ConfigurationResponse(BaseModel):
    app_config: dict
    monitored_config: List[dict]
    twitch_config: List[dict]

class MonitoredDomainUpdate(BaseModel):
    id: Optional[int] = None
    url: str
    status: str

class ConfigurationUpdateRequest(BaseModel):
    # AppConfig fields
    app_config_normal_user_login: Optional[str] = None
    app_config_hero_color: Optional[str] = None
    app_config_title_text: Optional[str] = None
    app_config_info_text: Optional[str] = None
    app_config_footer_text: Optional[str] = None
    app_config_discord_bot_token: Optional[str] = None
    app_config_ad_discord_bot_token: Optional[str] = None
    app_config_refresh_interval: Optional[int] = None
    app_config_cloudvar_resonite_user: Optional[str] = None
    app_config_cloudvar_resonite_pass: Optional[str] = None
    app_config_cloudvar_base_name: Optional[str] = None
    app_config_cloudvar_general_name: Optional[str] = None
    app_config_facet_url: Optional[str] = None

    # TwitchConfig fields
    twitch_config_client_id: Optional[str] = None
    twitch_config_secret: Optional[str] = None
    twitch_config_game_id: Optional[str] = None
    twitch_config_account_name: Optional[str] = None

    # MonitoredDomains - format: {domain_id: {url, status}}
    monitored_domains: Optional[dict] = None

def require_moderator_access(user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)) -> UserAuthModel:
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(
            status_code=403,
            detail="Moderator or administrator access required",
        )
    return user_auth

def require_administrator_access(user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)) -> UserAuthModel:
    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )
    return user_auth

@router_v2.get("/admin/events")
async def get_admin_events(
    request: Request,
    user_auth: UserAuthModel = Depends(require_moderator_access)
):

    # Only get Resonite events
    platform_filter = and_(
        Event.tags.ilike('%resonite%'),
        not_(Event.tags.ilike('%vrchat%'))
    )

    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now

    events = await Event().find(__order_by=['start_time'], __custom_filter=and_(time_filter, platform_filter))

    events_formatted = []
    for event in events:
        events_formatted.append({
            "id": str(event.id),
            "external_id": str(event.external_id),
            "name": event.name,
            "description": event.description,
            "session_image": event.session_image,
            "location_str": event.location,
            "location_web_session_url": event.location_web_session_url,
            "location_session_url": event.location_session_url,
            "start_time": event.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": event.end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if event.end_time else None,
            "community_name": event.community.name,
            "community_url": event.community.url,
            "tags": event.tags,
            "status": event.status,
        })

    return events_formatted

@router_v2.post("/admin/events/update_status")
async def update_event_status(data: EventUpdateStatusRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):

    result = await Event.update(
        filters=(Event.id == data.id),
        status=data.status
    )

    if not result:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"id": data.id, "status": data.status, "result": result}


@router_v2.post("/admin/users/update_status")
async def update_user_status(data: UserUpdateStatusRequest, user_auth: UserAuthModel = Depends(require_administrator_access)):

    from sqlalchemy import select, create_engine
    from sqlmodel import Session

    fields_to_update = {
        "is_superuser": data.is_superuser,
        "is_moderator": data.is_moderator,
        "updated_at": datetime.utcnow(),
    }

    session = await get_current_async_session()
    instances = []

    query = select(User).where(User.id == data.id)

    result = await session.execute(query)
    rows = result.unique().all()
    for row in rows:
        instance = row[0]
        for key, value in fields_to_update.items():
            setattr(instance, key, value)
        await session.commit()
        await session.refresh(instance)
        session.expunge(instance)
        instances.append(instance)

    result = True

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": data.id, "is_superuser": data.is_superuser, "is_moderator": data.is_moderator, "result": result}


@router_v2.get("/admin/communities/{community_id}")
async def get_community_details(community_id: str, user_auth: UserAuthModel = Depends(require_moderator_access)):

    communities = await Community().find(id__eq=community_id)
    if not communities:
        raise HTTPException(status_code=404, detail="Community not found.")
    if len(communities) > 1:
        raise HTTPException(status_code=500, detail="Multiple communities found with the same ID.")

    community = communities[0]

    return {
        "id": community.id,
        "name": community.name,
        "external_id": community.external_id,
        "platform": community.platform.value,
        "platform_on_remote": community.platform_on_remote,
        "url": community.url,
        "tags": community.tags,
        "description": community.default_description if not community.custom_description else community.custom_description,
        "is_custom_description": True if community.custom_description else False,
        "private_role_id": community.config.get("private_role_id", None),
        "private_channel_id": community.config.get("private_channel_id", None),
        "events_url": community.config.get("events_url", None),
    }


@router_v2.get("/admin/communities/", response_model=list[dict])
async def get_admin_communities_list(
    request: Request,
    type: str = Query(..., description="Type of community list to fetch ('event' or 'stream')"),
    user_auth: UserAuthModel = Depends(require_moderator_access)
):


    communities = []
    if type == 'event':
        communities = await Community().find(platform__in=events_platforms, configured__eq=True)
    elif type == 'stream':
        communities = await Community().find(platform__in=streams_platforms, configured__eq=True)
    else:
        raise HTTPException(status_code=400, detail="Invalid community type")

    communities_formatted = []
    for community in communities:
        communities_formatted.append({
            "id": str(community.id),
            "name": community.name,
            "external_id": community.external_id,
            "platform": community.platform.value,
            "url": community.url,
            "tags": community.tags,
            "description": community.custom_description if community.custom_description else community.default_description,
            "is_custom_description": True if community.custom_description else False,
            "logo": community.logo,
            "private_role_id": community.config.get("private_role_id", None),
            "private_channel_id": community.config.get("private_channel_id", None),
            "events_url": community.config.get("events_url", None),
            "platform_on_remote": community.platform_on_remote,
        })

    return communities_formatted

@router_v2.post("/admin/communities/")
async def create_community(data: CommunityRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):

    new_community = await Community().add(
        name=data.name,
        external_id=data.external_id,
        platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
        url=data.url,
        monitored=False,
        configured=True,
        tags=data.tags,
        custom_description=data.description,
        config={
            "private_role_id": data.private_role_id,
            "private_channel_id": data.private_channel_id,
            "events_url": data.events_url,
        },
    )

    return {"id": new_community.id, "message": "Community created successfully"}


@router_v2.patch("/admin/communities/{community_id}")
async def update_community(community_id: str, data: CommunityRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):


    import logging

    if data.platform == 'JSON Community Event' and data.selected_community_external_ids:
        for selected_community_id, selected_community_to_add in data.selected_community_external_ids.items():
            logging.info(f"{selected_community_id}: {selected_community_to_add}")
            if selected_community_to_add:
                logging.info(f"Let see to have the community {selected_community_id}")
                logging.info(f"Checking on {data.events_url}/v2/communities/{selected_community_id}")

                r = requests.get(f"{data.events_url}/v2/communities/{selected_community_id}")
                try:
                    data_r = r.json()
                    await Community.upsert(
                        _filter_field=['external_id', 'platform'],
                        _filter_value=[data_r['external_id'], CommunityPlatform.DISCORD],
                        name = data_r['name'],
                        platform=CommunityPlatform.DISCORD,
                        platform_on_remote=data_r['platform'],
                        external_id=data_r['external_id'],
                        monitored=False,
                        configured=True,
                        logo=data_r['icon'],
                        default_description=data_r['description'],
                        tags="public" if data_r['public'] else "private",
                        config={
                            "community_configurator": community_id
                        }
                    )
                except Exception as e:
                    logging.error(f"Cant unpack json {e}")

    updated = await Community.update(
        filters=(Community.id == community_id),
        name=data.name,
        external_id=data.external_id,
        platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
        url=data.url,
        tags=data.tags,
        custom_description=data.description if not data.resetDescription else None,
        config={
            "private_role_id": data.private_role_id,
            "private_channel_id": data.private_channel_id,
            "events_url": data.events_url,
        },
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community updated successfully"}


@router_v2.delete("/admin/communities/{community_id}")
async def delete_community(community_id: str, user_auth: UserAuthModel = Depends(require_moderator_access)):

    deleted = await Community.delete(id__eq=community_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community deleted successfully"}

@router_v2.get("/admin/setup/communities/discord/")
async def discord_communities_setup(user_auth: UserAuthModel = Depends(require_moderator_access)):

    discord_communities = await Community().find(platform__in=[CommunityPlatform.DISCORD], configured__eq=False)

    return discord_communities

@router_v2.post("/admin/setup/communities/discord/import/{community_id}")
async def discord_community_setup_import(community_id: str, data: DiscordImportRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):

    updated = await Community.update(
        filters=(Community.id == community_id),
        configured=True,
        tags="private" if data.visibility == "PRIVATE" else "public"
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community updated successfully"}


@router_v2.get("/admin/configuration")
async def get_admin_configuration(
    user_auth: UserAuthModel = Depends(require_administrator_access)
):

    async def load(object):
        session = await get_current_async_session()
        instances = []
        query = select(object)
        result = await session.execute(query)
        rows = result.unique().all()
        for row in rows:
            instances.append(row[0])
        return instances

    # Load monitored domains
    monitored_config_objects = await load(MonitoredDomain)
    monitored_config = [
        {"id": domain.id, "url": domain.url, "status": domain.status}
        for domain in monitored_config_objects
    ]

    # Load twitch config
    twitch_config_objects = await load(TwitchConfig)
    twitch_config = [
        {
            "id": tc.id,
            "client_id": tc.client_id,
            "secret": tc.secret,
            "game_id": tc.game_id,
            "account_name": tc.account_name
        }
        for tc in twitch_config_objects
    ]

    # Load app config
    app_config = await config_manager.app_config()

    return {
        "app_config": dict(app_config) if app_config else {},
        "monitored_config": monitored_config,
        "twitch_config": twitch_config
    }


@router_v2.post("/admin/configuration")
async def update_admin_configuration(
    data: dict,
    user_auth: UserAuthModel = Depends(require_administrator_access)
):

    # Process AppConfig
    app_config_data = {}
    for key, value in data.items():
        if key == 'app_config_normal_user_login':
            value = True if value == 'ENABLED' else False
        if key.startswith("app_config_"):
            app_config_data[key.replace("app_config_", "")] = value

    if app_config_data:
        await config_manager.update_app_config(**app_config_data)

    # Process Monitored Domains
    async def load(object):
        session = await get_current_async_session()
        instances = []
        query = select(object)
        result = await session.execute(query)
        rows = result.unique().all()
        for row in rows:
            instances.append(row[0])
        return instances

    # Process Monitored Domains (additions, updates, deletions)
    existing_monitored_domains = await load(MonitoredDomain)
    existing_domain_ids = {domain.id for domain in existing_monitored_domains}

    submitted_monitored_domains = {}
    for key, value in data.items():
        if key.startswith("monitored_config_"):
            parts = key.split('_')
            # Expected format: monitored_config_{id}_url or monitored_config_{id}_status
            # parts[2] is the ID ('new-X' or an integer)
            # parts[3:] is the field name ('url', 'status', etc)
            domain_id_str = parts[2]
            field_name = "_".join(parts[3:])

            if domain_id_str not in submitted_monitored_domains:
                submitted_monitored_domains[domain_id_str] = {}
            submitted_monitored_domains[domain_id_str][field_name] = value

    # Process updates and additions
    for domain_id_str, domain_data in submitted_monitored_domains.items():
        if domain_id_str.startswith("new-"):
            # New domain
            await config_manager.add_monitored_domain(
                url=domain_data.get('url'),
                status=domain_data.get('status')
            )
        else:
            # Existing domain
            domain_id = int(domain_id_str)
            if domain_id in existing_domain_ids:
                await config_manager.update_monitored_domain(domain_id, **domain_data)

    # Process deletions
    submitted_ids = {
        int(d_id) for d_id in submitted_monitored_domains.keys()
        if not d_id.startswith("new-")
    }
    for existing_id in existing_domain_ids:
        if existing_id not in submitted_ids:
            await config_manager.delete_monitored_domain(existing_id)

    # Process TwitchConfig
    twitch_config_data = {}
    for key, value in data.items():
        if key.startswith("twitch_config_"):
            twitch_config_data[key.replace("twitch_config_", "")] = value

    if twitch_config_data:
        await config_manager.update_twitch_config(**twitch_config_data)

    return {"message": "Configuration updated successfully"}


@router_v2.get("/admin/metrics")
async def get_admin_metrics(
    user_auth: UserAuthModel = Depends(require_administrator_access)
):

    today = date.today()
    yesterday = today - timedelta(days=1)
    past_week = today - timedelta(days=7)
    past_month = today - timedelta(days=30)

    session = await get_current_async_session()

    # Metrics by domain and endpoint (past week)
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

    # Version statistics
    versions_result = (
        await session.execute(
            select(Metrics.version, func.count())
            .group_by(Metrics.version)
        )
    ).all()

    versions = [
        {"version": version[0], "count": version[1]}
        for version in versions_result
    ]

    # Daily unique users (past week)
    daily_unique_users_result = await session.execute(
        select(
            func.date(Metrics.timestamp).label('date'),
            func.count(func.distinct(Metrics.hashed_ip)).label('count')
        ).where(
            func.date(Metrics.timestamp) >= past_week
        ).group_by(func.date(Metrics.timestamp))
    )
    daily_unique_users = {
        str(date): count
        for date, count in daily_unique_users_result.all()
    }

    # Convert to lists for easier frontend consumption
    daily_unique_users_labels = list(daily_unique_users.keys())
    daily_unique_users_data = list(daily_unique_users.values())

    # Calculate averages
    total_unique_users = sum(daily_unique_users.values())
    average_unique_users = (
        total_unique_users / len(daily_unique_users)
        if daily_unique_users else 0
    )
    last_day_unique_users = daily_unique_users.get(str(today), 0)

    # Hourly activity heatmap (past 30 days)
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

    # Initialize empty heatmap data
    days_of_week = 7
    hours_of_day = 24
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

    # Country data (yesterday)
    country_data_result = await session.execute(
        select(
            Metrics.country,
            func.count(func.distinct(Metrics.hashed_ip)).label('count')
        ).where(
            func.date(Metrics.timestamp) == yesterday
        ).group_by(Metrics.country)
    )
    country_data = [
        {"name": country, "value": count}
        for country, count in country_data_result.all()
    ]
    max_users = max([item["value"] for item in country_data], default=0)

    return {
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
        "hour_labels": hour_labels
    }
