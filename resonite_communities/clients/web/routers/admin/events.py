from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client

from resonite_communities.utils.config import ConfigManager

config_manager = ConfigManager()

router = APIRouter()

@router.get("/admin/events")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        return RedirectResponse(url="/")

    return templates.TemplateResponse("admin/events.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "app_config": await config_manager.app_config(),
        "request": request,
    })
