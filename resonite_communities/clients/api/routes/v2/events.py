from fastapi import Request, Depends, Header
from resonite_communities.clients.api.utils.formatter import FormatType, set_default_format, get_filtered_events, generate_events_response
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
import json
from typing import Optional

# TODO: Remove this when moving away from the Web client backend requesting the API instead of the frontend
async def get_user_auth_from_header_or_cookie(
    x_user_auth: Optional[str] = Header(None),
    user_auth_cookie: UserAuthModel = Depends(get_user_auth)
) -> Optional[UserAuthModel]:
    if x_user_auth:
        try:
            user_auth_data = json.loads(x_user_auth)
            return UserAuthModel(**user_auth_data)
        except json.JSONDecodeError:
            pass # Fallback to cookie auth if header is malformed
    return user_auth_cookie

@router_v2.get("/events")
async def get_events_v2(
    request: Request,
    format_type: FormatType = None,
    communities: str = "",
    user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)
):
    return generate_events_response(
        version="v2",
        format_type=set_default_format(version="v2", format_type=format_type),
        events=await get_filtered_events(request.url.hostname, "v2", communities, user_auth)
    )
