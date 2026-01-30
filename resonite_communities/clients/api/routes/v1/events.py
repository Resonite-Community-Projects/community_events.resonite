from fastapi import Request
from resonite_communities.clients.api.utils.formatter import FormatType, set_default_format, get_filtered_events, generate_events_response
from resonite_communities.clients.api.routes.routers import router_v1
from resonite_communities.utils.db import get_current_async_session


@router_v1.get("/events")
async def get_events_v1(request: Request, format_type: FormatType = None, communities: str = "", languages: str = ""):
    format_type = set_default_format(version="v1", format_type=format_type)
    session = await get_current_async_session()
    return generate_events_response(
        version="v1",
        format_type=set_default_format(version="v1", format_type=format_type),
        events=await get_filtered_events(request.url.hostname, "v1", communities, languages, session=session),
    )


@router_v1.get("/aggregated_events")
async def get_aggregated_events_v1(request: Request, format_type: FormatType = None, communities: str = ""):
    """Deprecated"""
    return await get_events_v1(request=request, format_type=format_type, communities=communities)
