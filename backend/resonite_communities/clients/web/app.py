import argparse
import logging
import re
import traceback
import base64
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from flask.logging import default_handler
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import case, and_, not_, or_
from starlette.templating import Jinja2Templates

from resonite_communities.clients import StandaloneApplication
from resonite_communities.clients.web.utils.discord import get_current_user, get_user_guilds, \
    get_user_roles_in_guild_safe
from resonite_communities.models.community import CommunityPlatform, Community
from resonite_communities.models.signal import Event, Stream
from resonite_communities.utils import Config

formatter = logging.Formatter(
    '[%(asctime)s] [%(module)s] '
    '[%(levelname)s] %(message)s',
    "%Y-%m-%d %H:%M:%S %z"
)

logger = logging.getLogger('community_events')
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
logger.handlers[0].setFormatter(formatter)

re_cloudx_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_url_match_compiled = re.compile('((?:http|https):\/\/[\w_-]+(?:(?:\.[\w_-]+)+)[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])')
re_discord_timestamp_match_compiled = re.compile('<t:(.*?)>')

env = Environment(loader=FileSystemLoader("resonite_communities/clients/web/templates"))

def format_datetime(value, format="%d %b %I:%M %p"):
    if value:
        return value.strftime(format)
    return

def detect_resonite_url(event):
    if event.location_session_url:
        return "<a href='{}'>{}</a>".format(
            event.location_session_url, event.location
        )
    return event.location

def detect_resonite_community(event):
    if event.community.url:
        return "<a href='{}'>{}</a>".format(
            event.community.url, event.community.name
        )
    return event.community.name

def parse_desciption(desc):
    try:
        desc = re.sub(
            re_url_match_compiled,
            "<a href='\\1'>\\1</a>",
            desc)
    except Exception:
        logger.error(traceback.format_exc())
    desc = desc.replace('\n', '<br>')
    return desc

def filter_tab_is_active(tab, current_tab):
    if tab == current_tab:
        return "is-active"
    return ""

def filter_tab_display(tab, current_tab):
    if tab == current_tab:
        return "block"
    return "none"

def filter_tag(tags):
    html_tags = ""
    if not tags:
        return ""
    tags = tags.split(',')
    tags = [tag for tag in tags if tag not in ["public", "resonite"]]
    for tag in tags:
        html_tags += f"<span class='tag is-info m-1'>{tag}</span>"
    return html_tags

def format_seconds(value: int) -> str:
    hours = value // 3600
    minutes = (value % 3600) // 60
    seconds = value % 60
    result = []
    if hours > 0:
        result.append(f"{hours}h")
    if minutes > 0:
        result.append(f"{minutes}min")
    if seconds > 0 or not result:
        result.append(f"{seconds}sec")
    return "".join(result)


env.filters["formatdatetime"] = format_datetime
env.filters["detect_location"] = detect_resonite_url
env.filters["detect_community"] = detect_resonite_community
env.filters["parse"] = parse_desciption
env.filters["tab_is_active"] = filter_tab_is_active
env.filters["tab_display"] = filter_tab_display
env.filters["tags"] = filter_tag
env.filters["format_seconds"] = format_seconds

templates = Jinja2Templates(env=env)

from starlette.responses import JSONResponse, RedirectResponse

from resonite_communities.auth.users import fastapi_users, auth_backend
from resonite_communities.auth.db import (
    create_db_and_tables,
)
from resonite_communities.auth.schemas import UserCreate, UserRead

from contextlib import asynccontextmanager
import secrets


current_active_user = fastapi_users.current_user(active=True, optional=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: Replace with alembic
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.secret_key = Config.SECRET

# Discord stuff
from httpx_oauth.clients.discord import DiscordOAuth2

discord_oauth = DiscordOAuth2(
    client_id=str(Config.Discord.client.id),
    client_secret=Config.Discord.client.secret,
    scopes=["identify", "guilds", "guilds.members.read", "email"]
)

oauth_clients = {
    "discord": {
        "client": discord_oauth,
        "redirect_uri": Config.Discord.client.redirect_uri
    }
}


@app.get('/auth/login/{provider}')
async def login(provider: str):
    oauth_client = oauth_clients.get(provider)
    if not oauth_client:
        return JSONResponse({"error": f"Unsupported provider: {provider}"}, status_code=400)

    state = secrets.token_urlsafe(16)

    from fastapi_users.router.oauth import generate_state_token
    state_data: dict[str, str] = {}
    state_token = generate_state_token(state_data, Config.SECRET)

    authorization_url = await oauth_client["client"].get_authorization_url(
        redirect_uri=oauth_client["redirect_uri"],
        state=state_token,
    )
    return RedirectResponse(authorization_url)

from resonite_communities.auth.db import User
from fastapi import Depends
from fastapi_users import models
from fastapi_users.authentication import Strategy

@app.get('/logout')
async def logout(
    request: Request,
    user: User = Depends(current_active_user),
    strategy: Strategy[models.UP, models.ID] = Depends(auth_backend.get_strategy),
):
    token = request.cookies.get("fastapiusersauth")
    response = RedirectResponse(url="/")
    await auth_backend.logout(strategy, user, token)
    response.delete_cookie("fastapiusersauth")
    return response

app.include_router(
    fastapi_users.get_oauth_router(
        discord_oauth,
        auth_backend,
        Config.SECRET,
    ),
    prefix="/auth/discord",
    tags=["auth"],
)

logger = logging.getLogger('uvicorn.error')

async def render_main(request: Request, user: User, tab: str):
    user_auth = None

    if user:
        import contextlib
        from resonite_communities.auth.db import DiscordAccount, get_async_session
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

    if user and user.is_superuser:
        # Superuser see all events
        event_visibility_filter = and_(time_filter, platform_filter)
    elif user:
        # Authenticated users see public events and private events from communities they have access to
        community_filter = or_(
            Event.tags.ilike('%public%'), # All public events
            and_( # Private events that the user has access to
                Event.tags.ilike('%private%'),
                Event.community_id.in_(user_auth.user_communities)
            )
        )

        event_visibility_filter = and_(time_filter, community_filter, platform_filter)
    else:
        # Only public events for non authenticated users
        private_filter = not_(Event.tags.ilike('%private%'))
        event_visibility_filter = and_(time_filter, private_filter, platform_filter)

    events = Event().find(__order_by=['start_time'], __custom_filter=event_visibility_filter)
    streams = Stream().find(
        __order_by=['start_time'],
        end_time__gtr_eq=datetime.utcnow(), end_time__less=datetime.utcnow() + timedelta(days=8)
    )
    streamers = Community().find(platform__in=[CommunityPlatform.TWITCH])
    communities = Community().find(platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON])
    user_communities = Community().find(id__in=user_auth.user_communities) if user_auth else []
    from copy import deepcopy
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

@app.get("/")
async def index(request: Request, user: User = Depends(current_active_user)):
    return await render_main(request=request, user=user, tab="Events")

@app.get("/about")
async def about(request: Request, user: User = Depends(current_active_user)):
    return render_main(request=request, user=user, tab="About")

@app.get("/streams")
async def streams(request: Request, user: User = Depends(current_active_user)):
    return render_main(request=request, user=user, tab="Streams")



import multiprocessing


def run():
    parser = argparse.ArgumentParser(description="Run the server")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0:8001",
        help="Bind address (default: 0.0.0.0:8001)",
        metavar="<IP:PORT>"
    )

    args = parser.parse_args()

    options = {
        "bind": args.address,
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()
