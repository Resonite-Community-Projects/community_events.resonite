from fastapi import Request
from resonite_communities.clients.api.utils.cache import request_key_builder
from resonite_communities.clients.api.utils.formatter import FormatType, set_default_format, get_filtered_events, generate_events_response

from fastapi_cache.decorator import cache

from fastapi_cache.coder import PickleCoder

from resonite_communities.clients.api.routes.routers import router_v1


@router_v1.get("/events")
def get_events_v1(request: Request, format_type: FormatType = None, communities: str = ""):
    format_type = set_default_format(version="v1", format_type=format_type)
    return generate_events_response(
        version="v1",
        format_type=set_default_format(version="v1", format_type=format_type),
        events=get_filtered_events(request.url.hostname, "v1", communities),
    )


@router_v1.get("/aggregated_events")
@cache(expire=1800, key_builder=request_key_builder, coder=PickleCoder)
def get_aggregated_events_v1(request: Request, format_type: FormatType = None, communities: str = ""):
    """Deprecated"""
    return get_events_v1(request=request, format_type=format_type, communities=communities)
