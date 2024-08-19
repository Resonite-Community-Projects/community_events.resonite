import os
import json
import logging
import re
import time
import traceback
import base64
from datetime import datetime

import pytz
import requests
import timeago
import toml
from apscheduler.schedulers.background import BackgroundScheduler
import dateutil
from dateutil.parser import parse
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask.logging import default_handler
from flask_discord import DiscordOAuth2Session, Unauthorized, DiscordOAuth2Scope
from fenkeysmanagement import KeyManager

from resonite_communities.utils import (
    Config,
    RedisClient,
)

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

app = Flask(
    __name__,
    template_folder="../templates",
)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"

app.secret_key = Config.SECRET_KEY
app.config["DISCORD_CLIENT_ID"] = Config.DISCORD_CLIENT_ID
app.config["DISCORD_CLIENT_SECRET"] = Config.DISCORD_CLIENT_SECRET
app.config["DISCORD_REDIRECT_URI"] = Config.DISCORD_REDIRECT_URI
app.config["DISCORD_BOT_TOKEN"] = Config.DISCORD_CLIENT_BOT_TOKEN
app.key_manager = KeyManager()

discord = DiscordOAuth2Session(app)

def check_perms(request):
    data_str = request.data.decode('utf-8')
    try:
        data_json = json.loads(data_str)
        if "auth_key" in data_json.keys():
            app.key_manager.reload_keys()
            if (
                app.key_manager.keys.get('key', data_json['auth_key'])
                and not app.key_manager.key_revoked(data_json['auth_key'])
            ):
                return True
        return False
    except json.decoder.JSONDecodeError:
        return False

@app.route("/login/")
def login():
    return discord.create_session(scopes=[DiscordOAuth2Scope.IDENTIFY, DiscordOAuth2Scope.GUILDS])

@app.route("/callback/")
def callback():
    discord.callback()
    user = discord.fetch_user()
    return redirect(url_for(".index"))

@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for(".index"))

@app.route("/logout/")
def logout():
    discord.revoke()
    return redirect(url_for(".index"))

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'), port=os.getenv('REDIS_PORT', 6379))

def get_communities_sorted_events(events, communities):
    """ Return only the events part of the communities indicated. """
    sorted_events = []
    for community in communities:
        for event in events:
            if event['community'] == community:
                sorted_events.append(event)
    return sorted_events

def get_communities_eventsa(communities, aggregated_events=False):
    """ Return all the events sorted by starting date."""
    if communities:
        if aggregated_events:
            events = getData.dict_aggregated_events
        else:
            events = getData.dict_events
        communities = communities.split(',')
        sorted_events = get_communities_sorted_events(
            events, communities
        )
        sorted_events.sort(key=lambda x: x['scheduled_start_time'])
        return getData._str_format(sorted_events, quick=True)
    else:
        if aggregated_events:
            return getData.str_aggregated_events
        else:
            return getData.str_events

def get_communities_events(communities, api_ver=1, aggregated_events=False):
    if not communities:
        if aggregated_events:
            events = rclient.get(f'aggregated_events_v{api_ver}')
        else:
            events = rclient.get(f'events_v{api_ver}')
    else:
        communities = communities.encode('utf-8').split(b',')
        if aggregated_events:
            events = rclient.get(f'aggregated_events_v{api_ver}')
        else:
            events = rclient.get(f'events_v{api_ver}')
        _events = []
        for event in events.split(f"{chr(29)}"):
            if event.split(f"{chr(30)}")[5] in communities:
                _events.append(event)
        events = f"{chr(29)}".join(_events)
    if not events:
        return ''
    return events

@app.route("/v1/events")
def get_events_v1():
    """ API endpoints for get events."""
    return get_communities_events(
        request.args.get('communities'),
    )

@app.route("/v1/aggregated_events")
def get_aggregated_events_v1():
    """ API endpoints for get aggregated_events."""
    return get_communities_events(
        request.args.get('communities'),
        aggregated_events=True,
    )

@app.route("/v2/events")
def get_events_v2():
    """ API endpoints for get events."""
    return get_communities_events(
        request.args.get('communities'),
        api_ver=2,
    )

@app.route("/v2/aggregated_events")
def get_aggregated_events_v2():
    """ API endpoints for get aggregated_events."""
    return get_communities_events(
        request.args.get('communities'),
        api_ver=2,
        aggregated_events=True,
    )

@app.route("/v2/communities")
def get_communities_v2():
    raw_communities = rclient.get(f'communities_v2')
    communities = []
    if raw_communities:
        communities = raw_communities.split(chr(29).encode('utf-8'))
        communities = list(filter(None, communities))
        communities = [community.decode('utf-8').split(chr(30)) for community in communities]
    return communities

@app.route('/clean', methods=["POST"])
def clean():
    if not check_perms(request):
        return 'permissions denied'
    rclient.client.set('events_v1', '')
    rclient.client.set('aggregated_events_v1', '')
    rclient.client.set('events_v2', '')
    rclient.client.set('aggregated_events_v2', '')
    return 'cleaned'

@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %I:%M %p"):
    try:
        return parse(value).strftime(format)
    except dateutil.parser._parser.ParserError:
        return ''

@app.template_filter('detect_location')
def detect_resonite_url(event):
    if event[4]:
        return "<a href='{}'>{}</a>".format(
            event[4], event[3]
        )
    return event[3]

@app.template_filter('detect_community')
def detect_resonite_url(event):
    if event[9]:
        return "<a href='{}'>{}</a>".format(
            event[9], event[8]
        )
    return event[8]

@app.template_filter('parse')
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

@app.template_filter('tab_is_active')
def filter_tab_is_active(tab, current_tab):
    if tab == current_tab:
        return "is-active"
    return ""

@app.template_filter('tab_display')
def filter_tab_display(tab, current_tab):
    if tab == current_tab:
        return "block"
    return "none"

@app.template_filter('tags')
def filter_tag(tags):
    html_tags = ""
    if not tags:
        return ""
    for tag in tags.split(','):
        html_tags += f"<span class='tag is-info m-1'>{tag}</span>"
    return html_tags

def render_main(tab):
    if not Config.SHOW_WEBUI:
        return ''
    with open("resonite_communities/static/images/icon.png", "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
    aggregated_events=aggregated_events=request.args.get('aggregated_events', False)
    user=None
    if Config.PRIVATE_DISCORDS:
        if not discord.authorized:
            return render_template('login.html', userlogo=logo_base64)
        aggregated_events=True
        user = discord.fetch_user()
    raw_events = get_communities_events(
        request.args.get('communities'),
        api_ver=2,
        aggregated_events=aggregated_events,
    )
    _events = []
    if raw_events:
        _events = raw_events.split(chr(29).encode('utf-8'))
    _events = list(filter(None, _events))
    _events = [event.decode('utf-8').split(chr(30)) for event in _events]
    user_guilds = []
    if Config.PRIVATE_DISCORDS:
        events = []
        _user_guilds = [guild.name for guild in discord.fetch_guilds()]
        for user_guild in _user_guilds:
            if user_guild not in Config.PRIVATE_DISCORDS:
                continue
            user_guilds.append(user_guild)
        if discord.authorized:
            for event in _events:
                if event[8] in Config.PRIVATE_DISCORDS and event[8] not in user_guilds:
                    continue
                events.append(event)
    else:
        events = _events
    raw_streams = rclient.get(f'stream_v2')
    streams = []
    if raw_streams:
        streams = raw_streams.split(chr(29).encode('utf-8'))
    streams = list(filter(None, streams))
    streams = [stream.decode('utf-8').split(chr(30)) for stream in streams]
    raw_streamers = rclient.get(f'streamers_v2')
    streamers = []
    if raw_streamers:
        streamers = raw_streamers.split(chr(29).encode('utf-8'))
    streamers = list(filter(None, streamers))
    streamers = [streamer.decode('utf-8').split(chr(30)) for streamer in streamers]
    communities = []
    raw_communities = rclient.get(f'communities_v2')
    if raw_communities:
        communities = raw_communities.split(chr(29).encode('utf-8'))
    communities = list(filter(None, communities))
    communities = [community.decode('utf-8').split(chr(30)) for community in communities]
    return render_template(
        'index.html',
        facet_url=Config.FACET_URL,
        events=events,
        communities=communities,
        streams=streams,
        streamers=streamers,
        tab=tab,
        user=user,
        user_guilds=user_guilds,
        userlogo=logo_base64,
    )

@app.route("/")
def index():
    return render_main(tab="Events")

@app.route("/about")
def about():
    return render_main(tab="About")

@app.route("/streams")
def streams():
    return render_main(tab="Streams")

import multiprocessing

from gunicorn.app.wsgiapp import WSGIApplication


class StandaloneApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)


def run():
    options = {
        "bind": "0.0.0.0:8000",
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        #"worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication("resonite_communities.server.web_client:app", options).run()