import calendar
from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import UUID



import requests
from requests.exceptions import RequestException, JSONDecodeError
from sqlalchemy import and_, not_, select, func
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Query
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.clients.api.utils.models import CommunityRequest
from resonite_communities.models.signal import Event
from resonite_communities.models.community import CommunityPlatform, Community, events_platforms, streams_platforms
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.config.models import MonitoredDomain, TwitchConfig

from resonite_communities.clients.api.routes.v2.admin import require_moderator_access
from resonite_communities.clients.api.routes.v2.admin import require_administrator_access
from resonite_communities.clients.api.routes.v2.admin import load

config_manager = ConfigManager()

logger = get_logger(__name__)

class DiscordImportRequest(BaseModel):
    id: str
    visibility: str


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
        "community_configurator": community.config.get("community_configurator", None),
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
    elif type == 'remote':
        platforms = [CommunityPlatform.JSON_COMMUNITY_EVENT]
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
            "enabled": community.enabled,
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

        config = {}
        if data.events_url:
            config["events_url"] = data.events_url
        if data.community_configurator:
            config["community_configurator"] = data.community_configurator
        if data.private_channel_id:
            config["private_channel_id"] = data.private_channel_id
        if data.private_role_id:
            config["private_role_id"] = data.private_role_id

        new_community = await Community.add(
            name=data.name,
            external_id=data.external_id,
            platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
            url=data.url,
            monitored=False,
            configured=True,
            enabled=True,
            tags=data.tags,
            languages=data.languages,
            custom_description=data.description,
            config=config,
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

    try:
        existing_communities = await Community.find(id=community_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching community {community_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not existing_communities:
        logger.warning(f"Community {community_id} not found for update")
        raise HTTPException(status_code=404, detail="Community not found")

    existing = existing_communities[0]

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
                    existing_remote = await Community.find(
                        external_id=response_data['external_id'],
                        platform=CommunityPlatform.DISCORD,
                    )
                    remote_config = dict(existing_remote[0].config) if existing_remote else {}
                    remote_config['community_configurator'] = str(community_id)
                    await Community.upsert(
                        _filter_field=['external_id', 'platform'],
                        _filter_value=[response_data['external_id'], CommunityPlatform.DISCORD],
                        name=response_data['name'],
                        platform=CommunityPlatform.DISCORD,
                        platform_on_remote=response_data['platform'],
                        external_id=response_data['external_id'],
                        monitored=False,
                        configured=True,
                        enabled=True,
                        logo=response_data['icon'],
                        default_description=response_data['description'],
                        tags=response_data['tags'],
                        languages=response_data['languages'],
                        config=remote_config,
                    )
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
        config = dict(existing.config) if existing.config else {}
        if data.events_url is not None:
            config['events_url'] = data.events_url
        if data.community_configurator is not None:
            config['community_configurator'] = data.community_configurator
        if data.private_channel_id is not None:
            config['private_channel_id'] = data.private_channel_id
        if data.private_role_id is not None:
            config['private_role_id'] = data.private_role_id

        update_fields = dict(
            name=data.name,
            external_id=data.external_id,
            platform=CommunityPlatform(data.platform.upper().replace(' ', '_')),
            config=config,
        )
        if data.url is not None:
            update_fields['url'] = data.url
        if data.tags is not None:
            update_fields['tags'] = data.tags
        if data.languages is not None:
            update_fields['languages'] = data.languages
        if data.enabled is not None:
            update_fields['enabled'] = data.enabled
        if data.description is not None or data.resetDescription:
            update_fields['custom_description'] = data.description if not data.resetDescription else None

        updated = await Community.update(
            filters=(Community.id == community_id),
            **update_fields,
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
        discord_communities = await Community.find(platform__in=[CommunityPlatform.DISCORD], configured__eq=False)
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
            enabled=True,
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