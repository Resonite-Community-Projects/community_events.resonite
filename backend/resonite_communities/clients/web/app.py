import os
import logging
import re
import traceback
import base64
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from aiohttp.log import client_logger
from discord.utils import oauth_url
from fastapi import FastAPI, Request
from fastapi_discord import DiscordOAuthClient, RateLimited, Unauthorized, User
from fastapi_discord.config import DISCORD_OAUTH_AUTHENTICATION_URL
from flask.logging import default_handler
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import case
from starlette.templating import Jinja2Templates

from resonite_communities.clients import StandaloneApplication
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

env = Environment(loader=FileSystemLoader("resonite_communities/client/templates"))

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

env.filters["formatdatetime"] = format_datetime
env.filters["detect_location"] = detect_resonite_url
env.filters["detect_community"] = detect_resonite_community
env.filters["parse"] = parse_desciption
env.filters["tab_is_active"] = filter_tab_is_active
env.filters["tab_display"] = filter_tab_display
env.filters["tags"] = filter_tag

templates = Jinja2Templates(env=env)

app = FastAPI()
discord = DiscordOAuthClient(
    client_id=Config.Discord.client.id,
    client_secret=Config.Discord.client.secret,
    redirect_uri=Config.Discord.client.redirect_uri,
    scopes=("identify", "guilds"),
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await discord.init()
    yield

@app.get("/login")
async def login():
    return {"url": discord.oauth_login_url}

@app.get("/callback")
async def callback(code: str):
    token, refresh_token = await discord.get_access_token(code)
    return {"access_token": token, "refresh_token": refresh_token}

logger = logging.getLogger('uvicorn.error')

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"

app.secret_key = Config.SECRET_KEY

def render_main(request, tab):
    if not Config.SHOW_WEBUI:
        return ''
    with open("resonite_communities/client/static/images/icon.png", "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
    user=None

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
            'user_guilds' : [],
            'userlogo' : logo_base64,
            'discord_auth_url': discord.oauth_login_url,
        }
    )

@app.get("/")
def index(request: Request):
    return render_main(request=request, tab="Events")

@app.get("/about")
def about(request: Request):
    return render_main(request=request, tab="About")

@app.get("/streams")
def streams(request: Request):
    return render_main(request=request, tab="Streams")

import multiprocessing


def run():
    options = {
        "bind": "0.0.0.0:8000",
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()