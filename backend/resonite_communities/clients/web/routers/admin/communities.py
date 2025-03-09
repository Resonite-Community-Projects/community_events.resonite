from copy import deepcopy

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.web.routers.admin.utils import UserAuthModel, get_user_auth

router = APIRouter()

@router.get("/admin/communities")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if user_auth is None:
        return RedirectResponse(url="/")

    return templates.TemplateResponse("admin/communities.html", {
        "user" : deepcopy(user_auth.discord_account),
        "request": request,
    })