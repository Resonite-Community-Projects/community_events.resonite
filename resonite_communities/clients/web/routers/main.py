from copy import deepcopy
import asyncio

from fastapi import APIRouter, Request, Depends

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client

from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.db import get_current_async_session

config_manager = ConfigManager()

router = APIRouter()

@router.get("/")
async def index(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):
    return await render_main(request=request, user_auth=user_auth, tab="Events")

@router.get("/streams")
async def about(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):
    return await render_main(request=request, user_auth=user_auth, tab="Streams")

@router.get("/about")
async def about(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):
    return await render_main(request=request, user_auth=user_auth, tab="About")

async def render_main(request: Request, user_auth: UserAuthModel, tab: str):

    session = await get_current_async_session()

    # Make concurrent API calls instead of sequential
    events, streams, all_communities = await asyncio.gather(
        api_client.get("/v2/events", user_auth=user_auth),
        api_client.get("/v2/streams", user_auth=user_auth),
        api_client.get("/v2/communities", {"include_all": True}, user_auth=user_auth)
    )

    # Client-side filtering
    streamers = [c for c in all_communities if c.get('platform') == 'TWITCH']
    communities = [c for c in all_communities if c.get('public') and c.get('platform') != 'TWITCH']
    user_communities = [c for c in all_communities if c['id'] in user_auth.discord_account.user_communities] if user_auth else []

    return templates.TemplateResponse(
        request = request,
        name = 'index.html',
        context = {
            "app_config": await config_manager.app_config(session=session),
            'events': events,
            'communities' : communities,
            'streams' : streams,
            'streamers' : streamers,
            'tab' : tab,
            'user' : deepcopy(user_auth),
            'user_communities' : user_communities,
            'retry_after' : user_auth.discord_account.discord_update_retry_after if user_auth else None,
            'userlogo' : logo_base64,
            'discord_auth_url': '/auth/login/discord',
        }
    )
