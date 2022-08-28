import json
import requests
import time
import toml
import re
import logging
import traceback

from dateutil.parser import parse
import pytz
from datetime import datetime
import timeago

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask import jsonify
from flask import request
from flask import render_template
from flask.logging import default_handler

from discord import Discord
from utils.google import GoogleCalendar


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

with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']
DISCORD_GUILDS_WHITELISTED = config['DISCORD_GUILDS_WHITELISTED']
CALENDARS_ACCEPTED = config['CALENDARS_ACCEPTED']
CREDENTIALS_FILE = config['CREDENTIALS_FILE']

class GetData:
    guilds = {}
    str_events = ''
    str_aggregated_events = ''
    dict_events = []
    dict_aggregated_events = []
    discord = Discord(DISCORD_BOT_TOKEN)
    guilds_whitelisted  = DISCORD_GUILDS_WHITELISTED

    def __init__(self):
        if CREDENTIALS_FILE:
            self.google = GoogleCalendar(CALENDARS_ACCEPTED, CREDENTIALS_FILE)

    def _clean_text(self, text):
        if text:
            text = text.replace('`', ' ')
            text = text.replace('\n\n', ' ')
            text = text.replace('\n\r', ' ')
            text = text.replace('\n', ' ')
            text = text.replace('\r', ' ')
        else:
            text = ''
        return text

    def _get_community_info(self, event):
        community = event['community'] if 'community' in event else event['guild_id']
        if community.isdigit():
            community = self.guilds[community]
        return community

    def _dict_format(self, events):
        """Formats events in dict."""
        data = []
        for index, event in enumerate(events):
            description = self._clean_text(event['description'])
            community = self._get_community_info(event)

            data.append(
                {'name': event['name'], 'description': description, 'entity_metadata': event['entity_metadata']['location'], 'scheduled_start_time': event['scheduled_start_time'], 'scheduled_end_time': event['scheduled_end_time'], 'community': community}
            )
        return data

    def _str_format(self, events, quick=False):
        """Formats events in str."""
        text_data = ""
        for index, event in enumerate(events):
            description = self._clean_text(event['description'])

            if quick:
                text_data += f"{event['name']}`{description}`{event['entity_metadata']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{event['community']}"
            else:
                community = self._get_community_info(event)

                text_data += f"{event['name']}`{description}`{event['entity_metadata']['location']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{community}"
            if index != len(events)-1:
                text_data += '\n\r'
        return text_data

    def _filter_neos_only_events(self, events):
        filtered_events = []
        for event in events:
            desc = self._clean_text(event['description'])
            name = self._clean_text(event['name'])
            location = ''
            if event['entity_metadata']:
                location = self._clean_text(event['entity_metadata']['location'])
            q = name + desc + location
            if q:
                q = q.replace(' ', '')
                q = q.lower()
            if 'neos' in q:
                filtered_events.append(event)
        return filtered_events

    def get_guilds(self):
        self.guilds = {}
        for guild in self.discord.get_guilds():
            self.guilds[guild['id']] = guild['name']

    def get(self):
        events = []
        aggregated_events = []
        self.get_guilds()
        for community in self.guilds.keys():
            if community not in self.guilds_whitelisted:
                continue
            try:
                events.extend(self.discord.list_guild_events(community))
            except Exception as e:
                pass
        for server in config['SERVERS_EVENT']:
            try:
                r = requests.get(server + '/v1/events')
            except Exception as err:
                logging.error(f'Error: {err}')
                continue
            if r.status_code != 200:
                logging.error(f'Error {r.status_code}: {r.text}')
                continue
            if not r.text:
                continue
            _server_events = r.text.split('\n\r')
            server_events = [event.split('`') for event in _server_events]
            for event in server_events:
                if len(event) == 6:
                    aggregated_events.extend([{
                        'name': event[0],
                        'description': event[1],
                        'entity_metadata': {'location': event[2]},
                        'scheduled_start_time': event[3],
                        'scheduled_end_time': event[4],
                        'community': event[5]
                    }])

        def clean_google_description(description):
            description = description.replace('<span>', ' ')
            description = description.replace('</span>', ' ')
            description = description.replace('<html-blob>', ' ')
            description = description.replace('</html-blob>', ' ')
            description = description.strip(' ')
            return description

        def parse_date(date):

            if 'date' in date:
                date = parse(date['date'])
                return date.replace(tzinfo=pytz.UTC).isoformat()
            else:
                date = date['dateTime']
                return parse(date).isoformat()

        if getattr(self, 'google', False):
            google_data = self.google.get_events()
            google_events = []
            for event in google_data[0]['items']:
                community, name = event['summary'].split('`')
                start_time = parse_date(event['start'])
                end_time = parse_date(event['end'])
                description = ''
                if 'description' in event:
                    description = clean_google_description(event['description'])
                google_events.extend(
                    [{
                        'name': name,
                        'description': description,
                        'entity_metadata': {'location': event['location']},
                        'scheduled_start_time': start_time,
                        'scheduled_end_time': end_time,
                        'community': community,
                    }]
                )
            events.extend(google_events)
        aggregated_events.extend(events)

        aggregated_events.sort(key=lambda x: x['scheduled_start_time'])
        aggregated_events = self._filter_neos_only_events(aggregated_events)
        self.dict_aggregated_events = self._dict_format(aggregated_events)
        self.str_aggregated_events = self._str_format(aggregated_events)

        events = self._filter_neos_only_events(events)
        events = sorted(events, key=lambda d: d['scheduled_start_time'])
        self.dict_events = self._dict_format(events)
        self.str_events = self._str_format(events)

getData = GetData()

getData.get()

sched = BackgroundScheduler(daemon=True)
sched.add_job(getData.get,'interval',minutes=5)
sched.start()

app = Flask(__name__)

def get_communities_sorted_events(events, communities):
    sorted_events = []
    for community in communities:
        for event in events:
            if event['community'] == community:
                sorted_events.append(event)
    return sorted_events

def get_communities_events(communities, aggregated_events=False):
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

@app.route("/v1/events")
def get_data():
    return get_communities_events(
        request.args.get('communities'),
    )

@app.route("/v1/aggregated_events")
def get_aggregated_data():
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
        a = re.search(re_discord_timestamp_match_compiled, desc)
        if a:
            timestamp,format = a.group(1).split(":")
            if format == 'R':
                date = datetime.fromtimestamp(int(timestamp))
                now = datetime.now()
                data = timeago.format(date, now)
                desc = re.sub(
                    re_discord_timestamp_match_compiled,
                    f"<code>{data}</code>",
                    desc)
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
    events = raw_events.split('\n\r')
    events = list(filter(None, events))
    events = [event.split('`') for event in events]
    return render_template('index.html', events=events)