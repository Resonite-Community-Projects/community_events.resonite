import contextlib
import base64
from copy import deepcopy
from datetime import datetime, timedelta

from sqlalchemy import case, and_, not_, or_
from fastapi import APIRouter, Request, Depends

from resonite_communities.models.signal import Event, Stream, EventStatus
from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session

config_manager = ConfigManager(get_session)

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

    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now

    # Only get Resonite events
    platform_filter = and_(
        Event.tags.ilike('%resonite%'),
        not_(Event.tags.ilike('%vrchat%'))
    )

    # Only get Events that are ACTIVE or READY
    status_filter = Event.status.in_((EventStatus.ACTIVE, EventStatus.READY))

    if user_auth and user_auth.is_superuser:
        # Superuser see all events
        event_visibility_filter = and_(time_filter, platform_filter, status_filter)
    elif user_auth:
        # Authenticated users see public events and private events from communities they have access to
        community_filter = or_(
            Event.tags.ilike('%public%'), # All public events
            and_( # Private events that the user has access to
                Event.tags.ilike('%private%'),
                Event.community_id.in_(user_auth.discord_account.user_communities)
            )
        )

        event_visibility_filter = and_(time_filter, community_filter, platform_filter, status_filter)
    else:
        # Only public events for non authenticated users
        private_filter = not_(Event.tags.ilike('%private%'))
        event_visibility_filter = and_(time_filter, private_filter, platform_filter, status_filter)

    events = Event().find(__order_by=['start_time'], __custom_filter=event_visibility_filter)
    streams = Stream().find(
        __order_by=['start_time'],
        end_time__gtr_eq=datetime.utcnow(), end_time__less=datetime.utcnow() + timedelta(days=8)
    )
    streamers = Community().find(platform__in=[CommunityPlatform.TWITCH])

    communities = Community().find(__custom_filter=Community.tags.ilike('%public%'), platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON])
    user_communities = Community().find(id__in=user_auth.discord_account.user_communities) if user_auth else []

    return templates.TemplateResponse(
        request = request,
        name = 'index.html',
        context = {
            "app_config": config_manager.db_config(),
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
