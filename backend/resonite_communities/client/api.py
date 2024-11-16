import json
from datetime import datetime
from enum import Enum

from dacite.types import is_instance
from fastapi import FastAPI, APIRouter, Depends, Response, HTTPException, Request

from resonite_communities.models.signal import Event, Stream

app = FastAPI()

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