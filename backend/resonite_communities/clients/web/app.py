import logging
import re
import traceback
import base64
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from flask.logging import default_handler
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import case
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
    for tag in tags.split(','):
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


current_active_user = fastapi_users.current_user(active=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: Replace with alembic
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Auth route /login and /logout

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Register route /register

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

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
    encoded_state = base64.urlsafe_b64encode(json.dumps({"state": state, "provider": provider}).encode()).decode()

    authorization_url = await oauth_client["client"].get_authorization_url(
        redirect_uri=oauth_client["redirect_uri"],
        state = encoded_state,
    )
    return RedirectResponse(authorization_url)



@app.get('/auth/callback')
async def callback(request: Request):
    code = request.query_params.get("code")
    encoded_state = request.query_params.get("state")

    if not code or not encoded_state:
        return JSONResponse({"error": "Missing code or state"}, status_code=400)

    try:
        decoded_state = base64.urlsafe_b64decode(encoded_state).decode()
        state_data = json.loads(decoded_state)
        provider = state_data["provider"]
        state = state_data["state"]
    except Exception as e:
        return JSONResponse({"error": "Failed to decode state", "details": str(e)}, status_code=400)

    if not provider:
        return JSONResponse({"error": "No provider found in state"}, status_code=400)

    oauth_client = oauth_clients.get(provider)
    if not oauth_client:
        return JSONResponse({"error": f"Unsupported provider: {provider}"}, status_code=400)

    token = await oauth_client["client"].get_access_token(code, redirect_uri=oauth_client["redirect_uri"])
    access_token = token.get("access_token")

    if not access_token:
        return JSONResponse({"error": "Failed to retrieve access token"}, status_code=400)\

    response = RedirectResponse(url="/")

    # TODO: Need to think harder about that the rate limit on this is really really bad

    user_data = get_current_user(access_token)
    user = {"name": user_data["username"], "avatar_url": user_data["avatar_url"]}
    guilds = get_user_guilds(access_token)

    private_events_access_communities = {'retry_after': 0, 'guilds': []}
    for guild in guilds:
        for configured_guild in Config.SIGNALS.DiscordEventsCollector:
            if str(configured_guild['external_id']) == str(guild['id']):
                private_role_id = configured_guild.get('config', {}).get('private_role_id')
                if private_role_id:
                    user_roles = get_user_roles_in_guild_safe(access_token, guild['id'])
                    if private_events_access_communities['retry_after'] < user_roles['retry_after']:
                        private_events_access_communities['retry_after'] = user_roles['retry_after']
                    for user_role in user_roles['ids']:
                        if str(user_role) == str(configured_guild.get('config', {}).get('private_role_id')):
                            private_events_access_communities['guilds'].append(guild['name'])

    cookie_data = {
        "user": user,
        "private_events_access_communities": private_events_access_communities,
    }

    # TODO: The data in this token MUST BE ENCRYPTED!
    response.set_cookie(
        key="user_data",
        value=json.dumps(cookie_data),
        httponly=True,
        secure=False,
        max_age=600
    )

    return response

logger = logging.getLogger('uvicorn.error')

app.secret_key = Config.SECRET_KEY

def render_main(request: Request, tab: str):
    cookie_data_str = request.cookies.get("user_data")
    private_events_access_communities = []
    user = None
    if cookie_data_str:
        cookie_data = json.loads(cookie_data_str)
        private_events_access_communities = cookie_data["private_events_access_communities"]
        user = cookie_data["user"]
    with open("resonite_communities/clients/web/static/images/icon.png", "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")


    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    event_visibility_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now

    events = Event().find(__order_by=['start_time'], __custom_filter=event_visibility_filter)
    streams = Stream().find(
        __order_by=['start_time'],
        end_time__gtr_eq=datetime.utcnow(), end_time__less=datetime.utcnow() + timedelta(days=8)
    )
    streamers = Community().find(platform__in=[CommunityPlatform.TWITCH])
    communities = Community().find(platform__in=[CommunityPlatform.DISCORD, CommunityPlatform.JSON])
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
            'user' : user,
            'user_guilds' : private_events_access_communities,
            'userlogo' : logo_base64,
            'discord_auth_url': '/auth/login/discord',
        }
    )

@app.get("/")
async def index(request: Request):
    return render_main(request=request, tab="Events")

@app.get("/about")
async def about(request: Request):
    return render_main(request=request, tab="About")

@app.get("/streams")
async def streams(request: Request):
    return render_main(request=request, tab="Streams")

import multiprocessing


def run():
    options = {
        "bind": "0.0.0.0:8000",
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()