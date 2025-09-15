from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.models.community import Community, CommunityPlatform, events_platforms, streams_platforms

from resonite_communities.utils.config import ConfigManager

config_manager = ConfigManager()

router = APIRouter()

# TODO: Look if this is still used
@router.get("/admin/communities")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        return RedirectResponse(url="/")

    events_communities = await Community().find(platform__in=events_platforms, configured__eq=True)
    streams_communities = await Community().find(platform__in=streams_platforms, configured__eq=True)

    return templates.TemplateResponse("admin/communities.html", {
        "userlogo" : logo_base64,
        "app_config": await config_manager.app_config(),
        "user" : deepcopy(user_auth),
        "events_communities": events_communities,
        "streams_communities": streams_communities,
        "request": request,
    })
