from fastapi import Request, Depends, Header
from resonite_communities.clients.api.utils.formatter import FormatType, set_default_format, get_filtered_events, generate_events_response
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.api.utils.auth import get_user_auth_from_header_or_cookie
from resonite_communities.utils.db import get_current_async_session
import json
from typing import Optional

@router_v2.get("/events")
async def get_events_v2(
    request: Request,
    format_type: FormatType = None,
    communities: str = "",
    languages: str = "",
    user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)
):
    session = await get_current_async_session()
    return generate_events_response(
        version="v2",
        format_type=set_default_format(version="v2", format_type=format_type),
        events=await get_filtered_events(request.url.hostname, "v2", communities, languages, user_auth, session=session)
    )
