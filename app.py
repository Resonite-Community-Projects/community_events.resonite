import os
import json
import logging
import re
import time
import traceback
from datetime import datetime

import pytz
import requests
import timeago
import toml
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.parser import parse
from flask import Flask, jsonify, render_template, request
from flask.logging import default_handler

from discord import Discord

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

rclient = RedisClient(host=os.getenv('REDIS_HOST', 'cache'))

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

def get_communities_events(communities, aggregated_events=False):
    if not communities:
        if aggregated_events:
            return rclient.get('aggregated_events_v1')
        return rclient.get('events_v1')
    else:
        communities = communities.encode('utf-8').split(b',')
        if aggregated_events:
            events = rclient.get('aggregated_events_v1')
        else:
            events = rclient.get('events_v1')
        _events = []
        for event in events.split(b'\n'):
            if event.split(b'`')[5] in communities:
                _events.append(event)
        return b"\n".join(_events)

@app.route("/v1/events")
def get_data():
    """ API endpoints for get events."""
    return get_communities_events(
        request.args.get('communities'),
    )

@app.route("/v1/aggregated_events")
def get_aggregated_data():
    """ API endpoints for get aggregated_events."""
    return get_communities_events(
        request.args.get('communities'),
        aggregated_events=True,
    )

@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %I:%M %p"):
    return parse(value).strftime(format)

@app.template_filter('detect_neos_url')
def detect_neos_url(event):
    world = event[2]
    if not world.startswith('http'):
        cloudx_url_match = re.search(re_cloudx_url_match_compiled, event[1])
        if cloudx_url_match:
            world = "<a href='{}'>{}</a>".format(
                cloudx_url_match.group(), world
            )
    else:
        world = "<a href='{}'>{}</a>".format(
                world, world
            )
    return world

@app.template_filter('parse')
def parse_desciption(desc):
    try:
        desc = re.sub(
            re_url_match_compiled,
            "<a href='\\1'>\\1</a>",
            desc)
        return desc
    except Exception:
        logging.error(traceback.format_exc())
        return desc

@app.route("/")
def index():
    raw_events = get_communities_events(
        request.args.get('communities'),
        aggregated_events=request.args.get('aggregated_events', False),
    )
    events = raw_events.split(b'\n')
    events = list(filter(None, events))
    events = [event.decode('utf-8').split('`') for event in events]
    return render_template('index.html', events=events)
