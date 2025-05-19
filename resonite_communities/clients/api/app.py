import argparse
import json
import multiprocessing
from datetime import datetime
from enum import Enum

from dacite.types import is_instance
from fastapi import APIRouter, Depends, Response, HTTPException, Request, FastAPI
from sqlalchemy import and_, not_, case

from resonite_communities.clients import StandaloneApplication
from resonite_communities.models.signal import Event, Stream, EventStatus
from resonite_communities.models.community import Community
from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.utils import Config, is_local_env
from resonite_communities.clients.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.utils.geoip import get_geoip_db_path

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi_cache.coder import PickleCoder

from redis import asyncio as aioredis

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url(Config.CACHE_URL)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())

router_v1 = APIRouter(prefix='/v1')
router_v2 = APIRouter(prefix='/v2')

# Multi domain management
# https://events.com will return only public events in the API
# https://private.events.com will return both public and private events in the API
# An event would be tagged as private directly in the database using tags.

# Version management
# Set as a route path
# /v1
# /v2
# /vX

# Format
# The V1 API should default to return TEXT
# The V2+ API should default to return JSON
# custom format would be via param /vX/events?format=<my format>

# Version management
# Set as a route path
# /v1
# /v2
# /vX

# Format
# The V1 API should default to return TEXT
# The V2+ API should default to return JSON
# custom format would be via param /vX/events?format=<my format>

class FormatType(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"

def set_default_format(
    version: str = "v1",
    format_type: FormatType | None = None,
):
    if not format_type:
        match version:
            case "v1":
                format_type = FormatType.TEXT
            case _:
                format_type = FormatType.JSON
    else:
        format_type = FormatType(format_type)

    return format_type

def get_filtered_events(
    host: str,
    version: str,
    communities: str,
):
    signals = []

    communities_filter = True
    if communities:
        communities = [community for community in communities.split(",")]
        communities_filter = Event.community.has(Community.name.in_(communities))

    if isinstance(Config.PUBLIC_DOMAIN, str):
        public_domains = [Config.PUBLIC_DOMAIN]
    else:
        public_domains = Config.PUBLIC_DOMAIN

    if isinstance(Config.PRIVATE_DOMAIN, str):
        private_domains = [Config.PRIVATE_DOMAIN]
    else:
        private_domains = Config.PRIVATE_DOMAIN

    if host in public_domains:
        domain_filter = not_(Event.tags.ilike("%private%"))
    elif host in private_domains:
        domain_filter = True
    else:
        msg = f"Unsupported domain: {host}."
        if is_local_env:
            msg += " You need to configure your hosts file for access to the locally to the HTTP API."
            msg += " See https://docs.resonite-communities.com/DeveloperGuide/server-configuration/"
        raise HTTPException(status_code=400, detail=msg)

    # Only get Resonite events
    platform_filter = and_(
        Event.tags.ilike('%resonite%'),
        not_(Event.tags.ilike('%vrchat%'))
    )

    # Only get Events that are ACTIVE or READY
    status_filter = Event.status.in_((EventStatus.ACTIVE, EventStatus.READY))

    if version == "v1":
        # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
        # If end_time is available, it will be used; otherwise, fallback to start_time.
        time_filter = case(
            (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
            else_=Event.start_time  # Otherwise, fallback to start_time
        ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now
        custom_filter=and_(communities_filter, domain_filter, platform_filter, status_filter, time_filter)
    else:
        custom_filter=and_(communities_filter, domain_filter, platform_filter, status_filter)

    # TODO: Instead of extend the signals variable, the Event and Stream find command should be one
    # SQL commend, optimization to order elements by date
    signals.extend(Event.find(__custom_filter=custom_filter, __order_by=["start_time"]))

    versioned_events = []
    for signal in signals:
        if version == "v1":
            versioned_events.append({
                "name": signal.name,
                #"description": signal.custom_description if signal.custom_description else signal.default_description,
                "description": signal.description,
                "location_str": signal.location,
                "start_time": signal.start_time.strftime("%Y/%m/%d %H:%M:%S+00:00"),
                "end_time": signal.end_time.strftime("%Y/%m/%d %H:%M:%S+00:00") if signal.end_time else None,
                "community_name": signal.community.name, # TODO: Connect this to a session
            })
        elif version == "v2":
            versioned_events.append({
                "name": signal.name,
                #"description": signal.custom_description if signal.custom_description else signal.default_description,
                "description": signal.description,
                "session_image": signal.session_image,
                "location_str": signal.location,
                "location_web_session_url": signal.location_web_session_url,
                "location_session_url": signal.location_session_url,
                "start_time": signal.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": signal.end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if signal.end_time else None,
                "community_name": signal.community.name, # TODO: Connect this to a session
                "community_url": signal.community.url,
                "tags": signal.tags,
                # source
            })
        else:
            raise HTTPException(status_code=400, detail="Unsupported version")

    return versioned_events

separators = {
    "v1": {"field": "`", "object": "\n"},
    "v2": {"field": chr(30), "object": chr(29)},
}

def clean_text(text):
    """ Remove all invalid characters for text_dumps. """
    if text:
        text = text.replace('`', ' ')
        text = text.replace('\n\n', ' ')
        text = text.replace('\n\r', ' ')
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
    else:
        text = ''
    return text

def text_dumps(events, version):
    """ Convert the Python Dictionary to a text string. """

    if version not in separators:
        raise ValueError("Unsported version.")
    field_separator = separators[version]['field']
    object_separator = separators[version]['object']

    formatted_items = []
    for event in events:
        formatted_event_values = []
        for event_key, event_value in event.items():

            # Convert list to a more usable text format
            if isinstance(event_value, list):
                event_value = ",".join(map(str, event_value))

            # Dict are not supported in TEXT format, silently pass to the next
            elif is_instance(event_value, dict):
                continue

            # Clean some event key of non wanted chars for the v1
            elif event_key in ['description'] and version == "v1":
                event_value = clean_text(event_value)

            # By default we convert anything else to string
            else:
                event_value = str(event_value)
            formatted_event_values.append(event_value)
        formatted_items.append(field_separator.join(formatted_event_values))
    return object_separator.join(formatted_items)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def generate_events_response(
        version: str,
        format_type: FormatType = Depends(set_default_format),
        events: list[dict] = Depends(get_filtered_events),
):
    match format_type:
        case FormatType.TEXT:
            return Response(
                text_dumps(events, version),
                media_type="text/plain",
            )
        case FormatType.JSON:
            return Response(
                json.dumps(events, cls=JSONEncoder),
                media_type="application/json",
            )
        case _:
            raise HTTPException(status_code=400, detail="Unsupported format")

def request_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    **kwargs,
):
    return ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])


@router_v1.get("/aggregated_events")
@cache(expire=1800, key_builder=request_key_builder, coder=PickleCoder)
def get_aggregated_events_v1(request: Request, format_type: FormatType = None, communities: str = ""):
    """Deprecated"""
    return get_events_v1(request=request, format_type=format_type, communities=communities)

@router_v1.get("/events")
def get_events_v1(request: Request, format_type: FormatType = None, communities: str = ""):
    format_type = set_default_format(version="v1", format_type=format_type)
    return generate_events_response(
        version="v1",
        format_type=set_default_format(version="v1", format_type=format_type),
        events=get_filtered_events(request.url.hostname, "v1", communities),
    )

@router_v2.get("/events")
def get_events_v2(request: Request, format_type: FormatType = None, communities: str = ""):
    return generate_events_response(
        version="v2",
        format_type=set_default_format(version="v2", format_type=format_type),
        events=get_filtered_events(request.url.hostname, "v2", communities)
    )

@router_v2.get("/communities")
def get_communities_v2():
    communities = Community().find(__custom_filter=Community.tags.ilike('%public%'), platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON])

    communities_formated = []
    for community in communities:
        communities_formated.append({
            "name": community.name,
            "description": community.custom_description if community.custom_description else community.default_description,
            "url": community.url,
            "icon": community.logo,
        })
    return communities_formated

# TODO: Temporary

from pydantic import BaseModel
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.models.signal import EventStatus

class EventUpdateStatusRequest(BaseModel):
    id: str
    status: EventStatus

@router_v2.post("/admin/events/update_status")
def update_event_status(data: EventUpdateStatusRequest, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        msg = f"Not authenticated."
        raise HTTPException(status_code=403, detail=msg)

    result = Event.update(
        filters=(Event.id == data.id),
        status=data.status
    )

    if not result:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"id": data.id, "status": data.status, "result": result}

@router_v2.get("/admin/communities/{community_id}")
def get_community_details(community_id: str, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
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
        "url": community.url,
        "tags": community.tags,
        "description": community.default_description if not community.custom_description else community.custom_description,
        "private_role_id": community.config.get("private_role_id", None),
        "private_channel_id": community.config.get("private_channel_id", None),
    }

from pydantic import BaseModel

class CommunityRequest(BaseModel):
    name: str
    external_id: str
    platform: str
    url: str
    tags: str
    description: str
    private_role_id: str | None = None
    private_channel_id: str | None = None

@router_v2.post("/admin/communities/")
def create_community(data: CommunityRequest, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(status_code=403, detail="Not authenticated.")

    new_community = Community().add(
        name=data.name,
        external_id=data.external_id,
        platform=CommunityPlatform(data.platform.upper()),
        url=data.url,
        tags=data.tags,
        custom_description=data.description,
        config={
            "private_role_id": data.private_role_id,
            "private_channel_id": data.private_channel_id,
        },
    )

    return {"id": new_community.id, "message": "Community created successfully"}

@router_v2.patch("/admin/communities/{community_id}")
def update_community(community_id: str, data: CommunityRequest, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(status_code=403, detail="Not authenticated.")

    updated = Community.update(
        filters=(Community.id == community_id),
        name=data.name,
        external_id=data.external_id,
        platform=CommunityPlatform(data.platform),
        url=data.url,
        tags=data.tags,
        description=data.description,
        config={
            "private_role_id": data.private_role_id,
            "private_channel_id": data.private_channel_id,
        },
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community updated successfully"}

@router_v2.delete("/admin/communities/{community_id}")
def delete_community(community_id: str, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(status_code=403, detail="Not authenticated.")

    deleted = Community.delete(filters=(Community.id == community_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Community not found")

    return {"id": community_id, "message": "Community deleted successfully"}

app.include_router(router_v1)
app.include_router(router_v2)

def run():
    parser = argparse.ArgumentParser(description="Run the server")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0:8000",
        help="Bind address (default: 0.0.0.0:8000)",
        metavar="<IP:PORT>"
    )

    args = parser.parse_args()

    options = {
        "bind": args.address,
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()