from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client
from resonite_communities.clients.web.utils.helpers import AttrDict

from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.db import get_current_async_session

config_manager = ConfigManager()

router = APIRouter()

@router.get("/admin/users")
async def get_users(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    session = await get_current_async_session()
    users = await api_client.get("/v2/admin/users", user_auth=user_auth, use_cache=False)

    # Convert dict responses to AttrDict for clean template dot notation
    users = [AttrDict(user) for user in users]

    return templates.TemplateResponse("admin/users.html", {
        "userlogo": logo_base64,
        "user": deepcopy(user_auth),
        "app_config": await config_manager.app_config(session=session),
        "users": users,
        "request": request,
    })
