import calendar
from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import UUID



import requests
from requests.exceptions import RequestException, JSONDecodeError
from sqlalchemy import case, and_, or_, not_, select, func, extract
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Query
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.models.metrics import Metrics, ClientType
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.clients.api.utils.auth import get_user_auth_from_header_or_cookie
from resonite_communities.clients.api.utils.models import CommunityRequest
from resonite_communities.auth.db import User, OAuthAccount
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.models.community import CommunityPlatform, Community, events_platforms, streams_platforms
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.config.models import MonitoredDomain, TwitchConfig


config_manager = ConfigManager()

logger = get_logger(__name__)

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

async def load(model_class, session):
    instances = []
    query = select(model_class).execution_options(populate_existing=True)
    result = await session.execute(query)
    rows = result.unique().all()
    for row in rows:
        instances.append(row[0])
    return instances


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
    community_id: Optional[str] = Query(None, description="Filter events by community ID"),
    platform_filter: Optional[str] = Query(None, description="Filter events by platform (e.g., 'resonite', 'vrchat', 'none', 'all')"),
    user_auth: UserAuthModel = Depends(require_moderator_access)
):
    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter_condition = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now

    custom_filters = [time_filter_condition]

    if platform_filter == 'all':
        pass
    elif platform_filter == 'none':
        # Filter for events with no platform tags
        # This checks if 'resonite' or 'vrchat' are NOT in the tags
        custom_filters.append(
            and_(
                not_(Event.tags.ilike('%resonite%')),
                not_(Event.tags.ilike('%vrchat%'))
            )
        )
    elif platform_filter:
        custom_filters.append(Event.tags.ilike(f'%{platform_filter}%'))
    else:
        # Default filter: Only get Resonite events, excluding VR Chat
        custom_filters.append(
            and_(
                Event.tags.ilike('%resonite%'),
                not_(Event.tags.ilike('%vrchat%'))
            )
        )

    if community_id:
        custom_filters.append(Event.community_id == community_id)

    try:
        events = await Event().find(__order_by=['start_time'], __custom_filter=and_(*custom_filters))
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching admin events: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

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
    try:
        result = await Event.update(
            filters=(Event.id == data.id),
            status=data.status
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating event {data.id} status: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not result:
        logger.warning(f"Event {data.id} not found for status update")
        raise HTTPException(status_code=404, detail="Event not found")

    logger.info(f"Event {data.id} status updated to {data.status}")
    return {"id": data.id, "status": data.status, "result": result}

@router_v2.delete("/admin/events/{event_id}")
async def delete_event(event_id: UUID, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        deleted = await Event.delete(id__eq=event_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not deleted:
        logger.warning(f"Event {event_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Event not found")

    logger.info(f"Event {event_id} deleted successfully")
    return {"id": event_id, "message": "Event deleted successfully"}


@router_v2.post("/admin/users/update_status")
async def update_user_status(data: UserUpdateStatusRequest, user_auth: UserAuthModel = Depends(require_administrator_access)):
    try:
        result = await User.update(
            filters=(User.id == data.id),
            is_superuser=data.is_superuser,
            is_moderator=data.is_moderator
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating user {data.id} permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not result:
        logger.warning(f"User {data.id} not found for status update")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User {data.id} permissions updated - superuser: {data.is_superuser}, moderator: {data.is_moderator}")
    return {"id": data.id, "message": "User permissions updated successfully"}

@router_v2.get("/admin/users")
async def get_admin_users(
    user_auth: UserAuthModel = Depends(require_administrator_access)
):
    session = await get_current_async_session()

    # Query users with joinedload for relationships
    try:
        query = select(User).options(
            joinedload(User.oauth_accounts).joinedload(OAuthAccount.discord_account)
        ).execution_options(populate_existing=True)

        result = await session.execute(query)
        rows = result.unique().all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching admin users: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    users = []
    for row in rows:
        user = row[0]

        # Build user data with relationships
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "is_moderator": user.is_moderator,
            "is_protected": user.is_protected,
            "oauth_accounts": []
        }

        # Add OAuth accounts with Discord data
        for oauth_account in user.oauth_accounts:
            oauth_data = {
                "id": str(oauth_account.id),
                "oauth_name": oauth_account.oauth_name,
                "access_token": oauth_account.access_token,
                "expires_at": oauth_account.expires_at,
                "refresh_token": oauth_account.refresh_token,
                "account_id": oauth_account.account_id,
                "account_email": oauth_account.account_email
            }

            # Add Discord account data if available
            if oauth_account.discord_account:
                discord = oauth_account.discord_account
                oauth_data["discord_account"] = {
                    "id": str(discord.id),
                    "name": discord.name,
                    "avatar_url": discord.avatar_url,
                    "user_communities": discord.user_communities,
                    "discord_update_retry_after": discord.discord_update_retry_after
                }
            else:
                oauth_data["discord_account"] = None

            user_data["oauth_accounts"].append(oauth_data)

        users.append(user_data)

    return users


@router_v2.get("/admin/communities/{community_id}")
async def get_community_details(community_id: UUID, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        communities = await Community().find(id__eq=community_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching community {community_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    if not communities:
        raise HTTPException(status_code=404, detail="Community not found")
    if len(communities) > 1:
        raise HTTPException(status_code=500, detail="Multiple communities found with the same ID")

    community = communities[0]

    return {
        "id": community.id,
        "name": community.name,
        "external_id": community.external_id,
        "platform": community.platform.value,
        "platform_on_remote": community.platform_on_remote,
        "url": community.url,
        "tags": community.tags,
        "languages": community.languages,
        "description": community.default_description if not community.custom_description else community.custom_description,
        "is_custom_description": bool(community.custom_description),
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
    session = await get_current_async_session()

    if type == 'event':
        platforms = events_platforms
    elif type == 'stream':
        platforms = streams_platforms
    else:
        raise HTTPException(status_code=400, detail="Invalid community type")

    try:
        # Fetch communities
        stmt = select(Community).where(Community.platform.in_(platforms), Community.configured == True)
        result = await session.execute(stmt)
        communities = result.scalars().all()
        community_ids = [community.id for community in communities]

        # Fetch event counts for these communities, filtering for Resonite platform only
        event_counts_stmt = select(Event.community_id, func.count(Event.id).label("event_count")) \
            .where(
                Event.community_id.in_(community_ids),
                and_(
                    Event.tags.ilike('%resonite%'),
                    not_(Event.tags.ilike('%vrchat%'))
                )
            ) \
            .group_by(Event.community_id)
        event_counts_result = await session.execute(event_counts_stmt)
        event_counts = {str(community_id): count for community_id, count in event_counts_result}
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching communities list: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    communities_formatted = []
    for community in communities:
        communities_formatted.append({
            "id": str(community.id),
            "name": community.name,
            "external_id": community.external_id,
            "platform": community.platform.value,
            "url": community.url,
            "tags": community.tags,
            "languages": community.languages,
            "description": community.custom_description if community.custom_description else community.default_description,
            "is_custom_description": bool(community.custom_description),
            "logo": community.logo,
            "private_role_id": community.config.get("private_role_id", None),
            "private_channel_id": community.config.get("private_channel_id", None),
            "events_url": community.config.get("events_url", None),
            "platform_on_remote": community.platform_on_remote,
            "event_count": event_counts.get(str(community.id), 0),
        })

    return communities_formatted

@router_v2.post("/admin/communities/")
async def create_community(data: CommunityRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):

    # check mandatory fields
    # TODO: This kind of test should be done with typing or something like this
    errors = []
    if not data.name:
        errors.append("Name is mandatory.")
    if not data.external_id:
        errors.append("External id is mandatory.")
    if not data.platform:
        errors.append("Platform is mandatory.")
    if (data.platform or '').upper().replace(' ', '_') != 'JSON_COMMUNITY_EVENT' and not data.languages:
        errors.append("At least one language is mandatory.")

    if errors:
        raise HTTPException(status_code=422, detail="".join(errors))

    try:
        new_community = await Community().add(
            name=data.name,
            external_id=data.external_id,
            platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
            url=data.url,
            monitored=False,
            configured=True,
            tags=data.tags,
            languages=data.languages,
            custom_description=data.description,
            config={
                "private_role_id": data.private_role_id,
                "private_channel_id": data.private_channel_id,
                "events_url": data.events_url,
            },
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error creating community {data.name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    logger.info(f"Community {new_community.id} created successfully: {data.name}")
    return {"id": new_community.id, "message": "Community created successfully"}


@router_v2.patch("/admin/communities/{community_id}")
async def update_community(community_id: UUID, data: CommunityRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):

    # check mandatory fields
    # TODO: This kind of test should be done with typing or something like this
    errors = []
    if not data.name:
        errors.append("Name is mandatory.")
    if not data.external_id:
        errors.append("External id is mandatory.")
    if not data.platform:
        errors.append("Platform is mandatory.")
    if (data.platform or '').upper().replace(' ', '_') != 'JSON_COMMUNITY_EVENT' and not data.languages:
        errors.append("At least one language is mandatory.")

    if errors:
        raise HTTPException(status_code=422, detail="".join(errors))

    if data.platform == 'JSON Community Event' and data.selected_community_external_ids:
        for selected_community_id, selected_community_to_add in data.selected_community_external_ids.items():
            if selected_community_to_add:
                try:
                    response = requests.get(
                        f"{data.events_url}/v2/communities/{selected_community_id}",
                        timeout=10
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully fetched community {selected_community_id} from remote server")
                    response_data = response.json()
                    logger.error(response_data)
                    await Community.upsert(
                        _filter_field=['external_id', 'platform'],
                        _filter_value=[response_data['external_id'], CommunityPlatform.DISCORD],
                        name=response_data['name'],
                        platform=CommunityPlatform.DISCORD,
                        platform_on_remote=response_data['platform'],
                        external_id=response_data['external_id'],
                        monitored=False,
                        configured=True,
                        logo=response_data['icon'],
                        default_description=response_data['description'],
                        tags=response_data['tags'],
                        languages=response_data['languages'],
                        config={
                            "community_configurator": str(community_id)
                        }
                    )
                    logger.error('dfdfdf')
                except RequestException as e:
                    logger.error(f"Failed to fetch community {selected_community_id}: {str(e)}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to fetch community data from remote server"
                    )
                except (JSONDecodeError, KeyError) as e:
                    logger.error(f"Invalid response format for community {selected_community_id}: {str(e)}")
                    raise HTTPException(
                        status_code=502,
                        detail="Invalid community data received from remote server"
                    )

    try:
        updated = await Community.update(
            filters=(Community.id == community_id),
            name=data.name,
            external_id=data.external_id,
            platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
            url=data.url,
            tags=data.tags,
            languages=data.languages,
            custom_description=data.description if not data.resetDescription else None,
            config={
                "private_role_id": data.private_role_id,
                "private_channel_id": data.private_channel_id,
                "events_url": data.events_url,
            },
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating community {community_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not updated:
        logger.warning(f"Community {community_id} not found for update")
        raise HTTPException(status_code=404, detail="Community not found")

    logger.info(f"Community {community_id} updated successfully: name={data.name}, external_id={data.external_id}, platform={data.platform}, url={data.url}, tags={data.tags}")
    return {"id": community_id, "message": "Community updated successfully"}


@router_v2.delete("/admin/communities/{community_id}")
async def delete_community(community_id: UUID, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        deleted = await Community.delete(id__eq=community_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting community {community_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not deleted:
        logger.warning(f"Community {community_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Community not found")

    logger.info(f"Community {community_id} deleted successfully")
    return {"id": community_id, "message": "Community deleted successfully"}

@router_v2.get("/admin/setup/communities/discord/")
async def discord_communities_setup(user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        discord_communities = await Community().find(platform__in=[CommunityPlatform.DISCORD], configured__eq=False)
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching Discord communities: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    return discord_communities

@router_v2.post("/admin/setup/communities/discord/import/{community_id}")
async def discord_community_setup_import(community_id: UUID, data: DiscordImportRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        updated = await Community.update(
            filters=(Community.id == community_id),
            configured=True,
            tags="private" if data.visibility == "PRIVATE" else "public"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error importing Discord community {community_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not updated:
        logger.warning(f"Community {community_id} not found for Discord import")
        raise HTTPException(status_code=404, detail="Community not found")

    logger.info(f"Discord community {community_id} imported successfully")
    return {"id": community_id, "message": "Community updated successfully"}


@router_v2.get("/admin/configuration")
async def get_admin_configuration(
    user_auth: UserAuthModel = Depends(require_administrator_access)
):
    session = await get_current_async_session()

    try:
        # Load monitored domains
        monitored_config_objects = await load(MonitoredDomain, session)
        monitored_config = [
            {"id": domain.id, "url": domain.url, "status": domain.status}
            for domain in monitored_config_objects
        ]

        # Load twitch config
        twitch_config_objects = await load(TwitchConfig, session)
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
        app_config = await config_manager.app_config(session=session)
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

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
    try:
        session = await get_current_async_session()

        # Process AppConfig
        app_config_data = {}
        for key, value in data.items():
            if key == 'app_config_normal_user_login':
                value = True if value == 'ENABLED' else False
            if key.startswith("app_config_"):
                app_config_data[key.replace("app_config_", "")] = value

        if app_config_data:
            await config_manager.update_app_config(session=session, **app_config_data)

        # Process Monitored Domains (additions, updates, deletions)
        existing_monitored_domains = await load(MonitoredDomain, session)
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
                    session=session,
                    url=domain_data.get('url'),
                    status=domain_data.get('status')
                )
            else:
                # Existing domain
                domain_id = int(domain_id_str)
                if domain_id in existing_domain_ids:
                    await config_manager.update_monitored_domain(session=session, domain_id=domain_id, **domain_data)

        # Process deletions
        submitted_ids = {
            int(d_id) for d_id in submitted_monitored_domains.keys()
            if not d_id.startswith("new-")
        }
        for existing_id in existing_domain_ids:
            if existing_id not in submitted_ids:
                await config_manager.delete_monitored_domain(session=session, domain_id=existing_id)

        # Process TwitchConfig
        twitch_config_data = {}
        for key, value in data.items():
            if key.startswith("twitch_config_"):
                twitch_config_data[key.replace("twitch_config_", "")] = value

        if twitch_config_data:
            await config_manager.update_twitch_config(session=session, **twitch_config_data)

    except SQLAlchemyError as e:
        logger.error(f"Database error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration update failed")

    logger.info(f"System configuration updated successfully")
    return {"message": "Configuration updated successfully"}


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
                func.date(Metrics.timestamp) >= past_week,
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
                func.date(Metrics.timestamp) >= past_week,
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
            .where(func.date(Metrics.timestamp) >= past_month)
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
                func.date(Metrics.timestamp) == yesterday,
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
                func.date(Metrics.timestamp) >= past_month,
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
            .where(func.date(Metrics.timestamp) >= past_month)
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
                func.date(Metrics.timestamp) >= past_month
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
