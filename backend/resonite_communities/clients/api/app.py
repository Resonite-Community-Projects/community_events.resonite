import argparse
import json
import multiprocessing
from datetime import datetime
from enum import Enum

from dacite.types import is_instance
from fastapi import APIRouter, Depends, Response, HTTPException, Request, FastAPI
from sqlalchemy import and_, not_

from resonite_communities.clients import StandaloneApplication
from resonite_communities.models.signal import Event, Stream
from resonite_communities.models.community import Community
from resonite_communities.utils import Config, is_local_env
from resonite_communities.clients.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.utils.geoip import get_geoip_db_path

app = FastAPI()

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

    if host == Config.PUBLIC_DOMAIN:
        domain_filter = not_(Event.tags.ilike("%private%"))
    elif host == Config.PRIVATE_DOMAIN:
        domain_filter = True
    else:
        msg = f"Unsupported domain: {host}."
        if is_local_env:
            msg += " You need to configure your hosts file for access to the locally to the HTTP API."
            msg += " See https://docs.resonite-communities.com/DeveloperGuide/server-configuration/"
        raise HTTPException(status_code=400, detail=msg)

    # Only get Resonite events
    platform_filter = Event.tags.ilike('%resonite%')

    signals.extend(Event.find(__custom_filter=and_(communities_filter, domain_filter, platform_filter)))

    if version != "v1":
        streams = Stream.find()

        signals.extend(streams)

    versioned_events = []
    for signal in signals:
        if version == "v1":
            versioned_events.append({
                "name": signal.name,
                "description": signal.description,
                "session_image": signal.session_image,
                "location_str": signal.location,
                "location_web_session_url": signal.location_web_session_url,
                "location_session_url": signal.location_session_url,
                "start_time": signal.start_time,
                "end_time": signal.end_time,
                "community_name": signal.community.name, # TODO: Connect this to a session
                "community_url": signal.community.url,
            })
        elif version == "v2":
            versioned_events.append({
                "name": signal.name,
                "start_time": signal.start_time,
                "end_time": signal.end_time,
                "tags": signal.tags,
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