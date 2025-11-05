import json
from copy import deepcopy
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse, RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client

from resonite_communities.utils.config import ConfigManager


config_manager = ConfigManager()

router = APIRouter()

@router.get("/admin/configuration")
async def get_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    config_data = await api_client.get("/v2/admin/configuration", user_auth=user_auth, use_cache=False)

    return templates.TemplateResponse("admin/configuration.html", {
        "userlogo": logo_base64,
        "user": deepcopy(user_auth),
        "api_url": config_manager.infrastructure_config.PUBLIC_DOMAIN,
        "app_config": config_data.get("app_config", {}),
        "monitored_config": config_data.get("monitored_config", []),
        "twitch_config": config_data.get("twitch_config", []),
        "request": request,
    })

@router.post("/admin/update/configuration")
async def update_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    # Get form data and convert to dict
    form_data = await request.form()
    data = dict(form_data)

    result = await api_client.post("/v2/admin/configuration", data, user_auth=user_auth)

    return JSONResponse(content=result)
