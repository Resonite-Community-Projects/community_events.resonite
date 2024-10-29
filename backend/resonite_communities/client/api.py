import json
from enum import Enum
from fastapi import FastAPI, APIRouter, Depends, Response, HTTPException, Query, Request

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
    format_type: FormatType | None = Query(None),
    version: str = "v1",
):
    if not format_type:
        match version:
            case "v1":
                format_type = FormatType.TEXT
            case _:
                format_type = FormatType.JSON
    else:
        format_type = FormatType.JSON

    return format_type

def get_filtered_events(
    host: str,
    version: str,
):
    # TODO: correctly get the information from the database
    events = [{"id": 1, "name": "Event 1", "tags": []}, {"id": 2, "name": "Event 2", "tags": ["private"]}]

    PUBLIC_DOMAIN = "events.com"
    PRIVATE_DOMAIN = "private.events.com"

    filtered_events = []

    if host == PUBLIC_DOMAIN:
        filtered_events = [event for event in events if 'private' not in event['tags']]
    elif host == PRIVATE_DOMAIN:
        filtered_events = events
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported domain: {host}")

    versioned_events = []
    for event in filtered_events:
        if version == "v1":
            versioned_events.append({
                "id": event['id'],
                "name": event['name'],
            })
        elif version == "v2":
            versioned_events.append({
                "id": event['id'],
                "name": event['name'],
                "tags": event['tags'],
            })
        else:
            raise HTTPException(status_code=400, detail="Unsupported version")

    return filtered_events

def generate_events_response(
        format_type: FormatType = Depends(set_default_format),
        events: list[dict] = Depends(get_filtered_events)
):
    # TODO: Correctly return the information in the wanted format
    match format_type:
        case FormatType.TEXT:
            return Response(json.dumps(events), media_type="text/plain")
        case FormatType.JSON:
            return Response(json.dumps(events), media_type="application/json")
        case _:
            raise HTTPException(status_code=400, detail="Unsupported format")

@router_v1.get("/events")
def get_events_v1(request: Request, format_type: FormatType = Depends(lambda: set_default_format(version="v1"))):
    return generate_events_response(
        format_type=format_type,
        events=get_filtered_events(request.url.hostname, "v1")
    )

@router_v2.get("/events")
def get_events_v2(request: Request, format_type: FormatType = Depends(lambda: set_default_format(version="v2"))):
    return generate_events_response(
        format_type=format_type,
        events=get_filtered_events(request.url.hostname, "v2")
    )
app.include_router(router_v1)
app.include_router(router_v2)