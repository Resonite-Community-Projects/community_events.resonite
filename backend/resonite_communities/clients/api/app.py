import json
import multiprocessing
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

from dacite.types import is_instance
from fastapi import FastAPI, APIRouter, Depends, Response, HTTPException, Request

from resonite_communities.clients import StandaloneApplication
from resonite_communities.models.signal import Event, Stream

from resonite_communities.auth.users import fastapi_users, auth_backend
from resonite_communities.auth.db import (
    User,
    create_db_and_tables,
)
from resonite_communities.auth.schemas import UserCreate, UserRead

@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: Replace with alembic
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

current_active_user = fastapi_users.current_user(active=True)

# Auth route /login and /logout

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Register route /register

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

@app.get(
    '/test',
)
def test(user: User = Depends(current_active_user)):
    return f'Hello {user.email}!'


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
):
    events = Event.find()

    PUBLIC_DOMAIN = "events.com"
    PRIVATE_DOMAIN = "private.events.com"

    filtered_events = []

    if host == PUBLIC_DOMAIN:
        filtered_events = [event for event in events if 'private' not in event.tags]
    elif host == PRIVATE_DOMAIN:
        filtered_events = events
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported domain: {host}")

    if version != "v1":
        streams = Stream.find()

        filtered_events.extend(streams)

    versioned_events = []
    for event in filtered_events:
        if version == "v1":
            versioned_events.append({
                "name": event.name,
                "description": event.description,
                "session_image": event.session_image,
                "location_str": event.location,
                "location_web_session_url": event.location_web_session_url,
                "location_session_url": event.location_session_url,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "community_name": event.community.name, # TODO: Connect this to a session
                "community_url": event.community.url,
            })
        elif version == "v2":
            versioned_events.append({
                "name": event.name,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "tags": event.tags,
            })
        else:
            raise HTTPException(status_code=400, detail="Unsupported version")

    return versioned_events

separators = {
    "v1": {"field": "`", "object": "\n"},
    "v2": {"field": chr(30), "object": chr(29)},
}

def format_dict_list(data, version):
    if version not in separators:
        raise ValueError("Unsported version.")
    field_separator = separators[version]['field']
    object_separator = separators[version]['object']

    formatted_items = []
    for item in data:
        formatted_values = []
        for value in item.values():
            # Convert list to a more usable text format
            if isinstance(value, list):
                formatted_values.append(",".join(map(str, value)))
            elif is_instance(value, dict):
                # We do not support dict
                # Silently pass to the next value
                continue
            else:
                formatted_values.append(str(value))
        formatted_items.append(field_separator.join(formatted_values))
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
                format_dict_list(events, version),
                media_type="text/plain",
            )
        case FormatType.JSON:
            return Response(
                json.dumps(events, cls=JSONEncoder),
                media_type="application/json",
            )
        case _:
            raise HTTPException(status_code=400, detail="Unsupported format")

@router_v1.get("/events")
def get_events_v1(request: Request, format_type: FormatType = None):
    format_type = set_default_format(version="v1", format_type=format_type)
    return generate_events_response(
        version="v1",
        format_type=set_default_format(version="v1", format_type=format_type),
        events=get_filtered_events(request.url.hostname, "v1"),
    )

@router_v2.get("/events")
def get_events_v2(request: Request, format_type: FormatType = None):
    return generate_events_response(
        version="v2",
        format_type=set_default_format(version="v2", format_type=format_type),
        events=get_filtered_events(request.url.hostname, "v2")
    )
app.include_router(router_v1)
app.include_router(router_v2)

def run():
    options = {
        "bind": "0.0.0.0:8000",
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()