import contextlib
import base64
from copy import deepcopy
from datetime import datetime, timedelta

from sqlalchemy import case, and_, not_, or_
from fastapi import APIRouter, Request, Depends

from resonite_communities.auth.db import User, DiscordAccount, get_async_session
from resonite_communities.auth.users import optional_current_active_user
from resonite_communities.models.signal import Event, Stream, EventStatus
from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.utils import Config
from resonite_communities.clients.web.utils.templates import templates

router = APIRouter()

@router.get("/")
async def index(request: Request, user: User = Depends(optional_current_active_user)):
    return await render_main(request=request, user=user, tab="Events")

@router.get("streams")
async def about(request: Request, user: User = Depends(optional_current_active_user)):
    return await render_main(request=request, user=user, tab="Streams")

@router.get("/about")
async def about(request: Request, user: User = Depends(optional_current_active_user)):
    return await render_main(request=request, user=user, tab="About")

async def render_main(request: Request, user: User, tab: str):
    user_auth = None

    if user:
        get_async_session_context = contextlib.asynccontextmanager(get_async_session)

        async with get_async_session_context() as session:
            for user_oauth_account in user.oauth_accounts:
                if user_oauth_account.oauth_name == "discord":
                    user_auth = await session.get(DiscordAccount, user_oauth_account.discord_account_id)
                    break

    with open("resonite_communities/clients/web/static/images/icon.png", "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")


    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now

    # Only get Resonite events
    platform_filter = Event.tags.ilike('%resonite%')

    # Only get Events that are ACTIVE or READY
    status_filter = Event.status.in_((EventStatus.ACTIVE, EventStatus.READY))

    if user and user.is_superuser:
        # Superuser see all events
        event_visibility_filter = and_(time_filter, platform_filter, status_filter)
    elif user:
        # Authenticated users see public events and private events from communities they have access to
        community_filter = or_(
            Event.tags.ilike('%public%'), # All public events
            and_( # Private events that the user has access to
                Event.tags.ilike('%private%'),
                Event.community_id.in_(user_auth.user_communities)
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
    communities = Community().find(platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON])
    user_communities = Community().find(id__in=user_auth.user_communities) if user_auth else []

    return templates.TemplateResponse(
        request = request,
        name = 'index.html',
        context = {
            'facet_url': Config.FACET_URL,
            'events': events,
            'communities' : communities,
            'streams' : streams,
            'streamers' : streamers,
            'tab' : tab,
            'user' : deepcopy(user_auth) if user_auth else None,
            'user_communities' : user_communities,
            'retry_after' : user_auth.discord_update_retry_after if user_auth else None,
            'userlogo' : logo_base64,
            'discord_auth_url': '/auth/login/discord',
        }
    )
