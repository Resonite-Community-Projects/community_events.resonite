from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.models.community import Community, CommunityPlatform
router = APIRouter()

# TODO: Look if this is still used
@router.get("/admin/communities")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    events_communities = Community().find(platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON], configured__eq=True)
    streams_communities = Community().find(platform__in=[CommunityPlatform.TWITCH], configured__eq=True)

    return templates.TemplateResponse("admin/communities.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "events_communities": events_communities,
        "streams_communities": streams_communities,
        "request": request,
    })

