from typing import Optional
from fastapi import Header, Depends
import json
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth


# TODO: Remove this when moving away from the Web client backend requesting the API instead of the frontend
async def get_user_auth_from_header_or_cookie(
    x_user_auth: Optional[str] = Header(None),
    user_auth_cookie: UserAuthModel = Depends(get_user_auth)
) -> Optional[UserAuthModel]:
    """
    Get user authentication from either X-User-Auth header (for web client backend)
    or from cookie/session (for direct frontend access).
    """
    if x_user_auth:
        try:
            user_auth_data = json.loads(x_user_auth)
            return UserAuthModel(**user_auth_data)
        except json.JSONDecodeError:
            pass  # Fallback to cookie auth if header is malformed
    return user_auth_cookie
