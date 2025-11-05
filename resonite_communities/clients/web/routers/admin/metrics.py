from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client

from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.db import get_current_async_session

config_manager = ConfigManager()

router = APIRouter()

@router.get("/admin/metrics")
async def get_metrics(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    session = await get_current_async_session()
    # Fetch metrics from API
    metrics_data = await api_client.get("/v2/admin/metrics", user_auth=user_auth, use_cache=False)

    return templates.TemplateResponse("admin/metrics.html", {
        "userlogo": logo_base64,
        "user": deepcopy(user_auth),
        "request": request,
        "metrics_domains": metrics_data.get("metrics_domains", {}),
        "versions": metrics_data.get("versions", []),
        "daily_unique_users_labels": metrics_data.get("daily_unique_users_labels", []),
        "daily_unique_users_data": metrics_data.get("daily_unique_users_data", []),
        "average_unique_users": metrics_data.get("average_unique_users", 0),
        "last_day_unique_users": metrics_data.get("last_day_unique_users", 0),
        "country_data": metrics_data.get("country_data", []),
        "max_users": metrics_data.get("max_users", 0),
        "heatmap_data": metrics_data.get("heatmap_data", []),
        "day_labels": metrics_data.get("day_labels", []),
        "hour_labels": metrics_data.get("hour_labels", []),
        "app_config": await config_manager.app_config(session=session),
    })
