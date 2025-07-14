from copy import deepcopy
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse
from sqlalchemy import case, and_

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import Event
from resonite_communities.auth.db import User
from resonite_communities.utils import Config

router = APIRouter()

@router.get("/admin/users")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    from sqlalchemy import select, create_engine
    from sqlmodel import Session

    engine = create_engine(Config.DATABASE_URL, echo=False)

    from sqlalchemy.orm import joinedload
    from resonite_communities.auth.db import OAuthAccount

    with Session(engine) as session:
        instances = []
        query = select(User).options(joinedload(User.oauth_accounts).joinedload(OAuthAccount.discord_account))
        print(query)

        rows = session.exec(query).unique().all()
        for row in rows:
            instances.append(row[0])
        users = instances

    try:
        api_url = Config.PUBLIC_DOMAIN[0]
    except KeyError:
        api_url = None

    if api_url and api_url.endswith(".local"):
        api_url = f"http://{api_url}"
    else:
        api_url = f"https://{api_url}"

    for user in users:
        print(user.oauth_accounts[0].discord_account.name)

    return templates.TemplateResponse("admin/users.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "api_url": Config.PUBLIC_DOMAIN,
        "users": users,
        "request": request,
    })

