from resonite_communities.clients.api.routes.routers import router_v2
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Request
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.models.signal import EventStatus
from resonite_communities.auth.db import User
from datetime import datetime
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.models.community import CommunityPlatform, Community, events_platforms, streams_platforms
from resonite_communities.utils.tools import is_local_env
from resonite_communities.clients.api.utils.models import CommunityRequest
from pydantic import BaseModel

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session
Config = ConfigManager(get_session).config()


from fastapi import Query

import requests

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

@router_v2.post("/admin/events/update_status")
def update_event_status(data: EventUpdateStatusRequest, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        msg = f"Not authenticated."
        raise HTTPException(status_code=403, detail=msg)

    result = Event.update(
        filters=(Event.id == data.id),
        status=data.status
    )

    if not result:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"id": data.id, "status": data.status, "result": result}


@router_v2.post("/admin/users/update_status")
def update_user_status(data: UserUpdateStatusRequest, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        msg = f"Not authenticated."
        raise HTTPException(status_code=403, detail=msg)

    from sqlalchemy import select, create_engine
    from sqlmodel import Session

    engine = create_engine(Config.DATABASE_URL, echo=False)

    fields_to_update = {
        "is_superuser": data.is_superuser,
        "is_moderator": data.is_moderator,
        "updated_at": datetime.utcnow(),
    }

    with Session(engine) as session:
        instances = []

        query = select(User).where(User.id == data.id)

        rows = session.exec(query).unique().all()
        for row in rows:
            instance = row[0]
            for key, value in fields_to_update.items():
                print(f"Setting {key} = {value} (type: {type(value)})")
                setattr(instance, key, value)
            session.commit()
            session.refresh(instance)
            session.expunge(instance)
            instances.append(instance)

    print(instances)

    result = True

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": data.id, "is_superuser": data.is_superuser, "is_moderator": data.is_moderator, "result": result}


@router_v2.get("/admin/communities/{community_id}")
def get_community_details(community_id: str, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    communities = Community().find(id__eq=community_id)
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
def get_admin_communities_list(
    request: Request,
    type: str = Query(..., description="Type of community list to fetch ('event' or 'stream')"),
    user_auth: UserAuthModel = Depends(get_user_auth)
):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    communities = []
    if type == 'event':
        communities = Community().find(platform__in=events_platforms, configured__eq=True)
    elif type == 'stream':
        communities = Community().find(platform__in=streams_platforms, configured__eq=True)
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
def create_community(data: CommunityRequest, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    new_community = Community().add(
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
def update_community(community_id: str, data: CommunityRequest, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")


    import logging

    if data.platform == 'JSON Community Event' and data.selected_community_external_ids:
        for selected_community_id, selected_community_to_add in data.selected_community_external_ids.items():
            logging.error(f"{selected_community_id}: {selected_community_to_add}")
            if selected_community_to_add:
                logging.error(f"Let see to have the community {selected_community_id}")
                logging.error(f"Checking on {data.events_url}/v2/communities/{selected_community_id}")

                r = requests.get(f"{data.events_url}/v2/communities/{selected_community_id}")
                try:
                    data_r = r.json()
                    Community.upsert(
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

    updated = Community.update(
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
def delete_community(community_id: str, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    deleted = Community.delete(id__eq=community_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community deleted successfully"}

@router_v2.get("/admin/setup/communities/discord/")
def discord_communities(user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    discord_communities = Community().find(platform__in=[CommunityPlatform.DISCORD], configured__eq=False)

    return discord_communities

@router_v2.post("/admin/setup/communities/discord/import/{community_id}")
def discord_communities(community_id: str, data: DiscordImportRequest, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(status_code=403, detail="Not authenticated.")

    updated = Community.update(
        filters=(Community.id == community_id),
        configured=True,
        tags="private" if data.visibility == "PRIVATE" else "public"
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community updated successfully"}


