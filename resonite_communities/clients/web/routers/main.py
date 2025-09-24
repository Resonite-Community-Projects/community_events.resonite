from copy import deepcopy
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends

from resonite_communities.models.signal import Stream
from resonite_communities.models.community import CommunityPlatform, Community, events_platforms
from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.clients.web.utils.api_client import api_client

from resonite_communities.utils.config import ConfigManager

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

    events = await api_client.get("/v2/events", user_auth=user_auth)

    streams = await Stream().find(
        __order_by=['start_time'],
        end_time__gtr_eq=datetime.utcnow(), end_time__less=datetime.utcnow() + timedelta(days=8)
    )
    streamers = await Community().find(platform__in=[CommunityPlatform.TWITCH])

    communities = await Community().find(__custom_filter=Community.tags.ilike('%public%'), platform__in=events_platforms)
    user_communities = await Community().find(id__in=user_auth.discord_account.user_communities) if user_auth else []

    return templates.TemplateResponse(
        request = request,
        name = 'index.html',
        context = {
            "app_config": await config_manager.app_config(),
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
