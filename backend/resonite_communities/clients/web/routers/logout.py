from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse
from fastapi_users import models
from fastapi_users.authentication import Strategy

from resonite_communities.auth.db import User
from resonite_communities.auth.users import (
    optional_current_active_user,
    auth_backend,
)

router = APIRouter()

@router.get('/logout')
async def logout(
    request: Request,
    user: User = Depends(optional_current_active_user),
    strategy: Strategy[models.UP, models.ID] = Depends(auth_backend.get_strategy),
):
    token = request.cookies.get("fastapiuserauth")
    response = RedirectResponse(url="/")
    await auth_backend.logout(strategy, user, token)
    response.delete_cookie("fastapiuserauth")
    return response