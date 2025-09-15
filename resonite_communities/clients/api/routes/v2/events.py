from fastapi import Request
from resonite_communities.clients.api.utils.formatter import FormatType, set_default_format, get_filtered_events, generate_events_response
from resonite_communities.clients.api.routes.routers import router_v2

@router_v2.get("/events")
async def get_events_v2(request: Request, format_type: FormatType = None, communities: str = ""):
    return generate_events_response(
        version="v2",
        format_type=set_default_format(version="v2", format_type=format_type),
        events=await get_filtered_events(request.url.hostname, "v2", communities)
    )
