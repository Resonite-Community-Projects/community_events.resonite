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
from flask import Flask, jsonify, render_template, request
from flask.logging import default_handler

from utils import Config

formatter = logging.Formatter(
    '[%(asctime)s] [%(module)s] '
    '[%(levelname)s] %(message)s',
    "%Y-%m-%d %H:%M:%S %z"
)

root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(default_handler)
root.handlers[0].setFormatter(formatter)

re_cloudx_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_url_match_compiled = re.compile('((?:http|https):\/\/[\w_-]+(?:(?:\.[\w_-]+)+)[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])')
re_discord_timestamp_match_compiled = re.compile('<t:(.*?)>')

app = Flask(__name__)

from utils import RedisClient

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
    return rclient.get('communities_v2') or ''

@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %I:%M %p"):
    try:
        return parse(value).strftime(format)
    except dateutil.parser._parser.ParserError:
        return ''

@app.template_filter('detect_location')
def detect_neos_url(event):
    if event[4]:
        return "<a href='{}'>{}</a>".format(
            event[4], event[3]
        )
    return event[3]

@app.template_filter('detect_community')
def detect_neos_url(event):
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
        logging.error(traceback.format_exc())
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

def render_main(tab):
    if not Config.SHOW_WEBUI:
        return ''
    raw_events = get_communities_events(
        request.args.get('communities'),
        api_ver=2,
        aggregated_events=request.args.get('aggregated_events', False),
    )
    events = []
    if raw_events:
        events = raw_events.split(chr(29).encode('utf-8'))
    events = list(filter(None, events))
    events = [event.decode('utf-8').split(chr(30)) for event in events]

    raw_streams = rclient.get(f'stream_v2')
    streams = []
    if raw_streams:
        streams = raw_streams.split(chr(29).encode('utf-8'))
    streams = list(filter(None, streams))
    streams = [stream.decode('utf-8').split(chr(30)) for stream in streams]
    with open("static/images/icon.png", "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
    return render_template('index.html', events=events, streams=streams, tab=tab, logo=logo_base64)

@app.route("/")
def index():
    return render_main(tab="Events")

@app.route("/about")
def about():
    return render_main(tab="About")

@app.route("/streams")
def streams():
    return render_main(tab="Streams")