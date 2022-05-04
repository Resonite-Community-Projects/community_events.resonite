import json
import requests
import time
import toml

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask import jsonify

from discord import Discord

with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']

class GetData:
    guilds = {}
    events = ''
    aggregated_events = ''
    discord = Discord(DISCORD_BOT_TOKEN)

    def _format(self, events):
        text_data = ""
        for index, event in enumerate(events):
            description = event['description']
            if description:
                description = description.replace('`', ' ')
                description = description.replace('\n\n', ' ')
                description = description.replace('\n\r', ' ')
                description = description.replace('\n', ' ')
                description = description.replace('\r', ' ')
            else:
                description = ''

            if event['guild_id'].isdigit():
                guild_id = self.guilds[event['guild_id']]
            else:
                guild_id = event['guild_id']
            text_data += f"{event['name']}`{description}`{event['entity_metadata']['location']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{guild_id}"
            if index != len(events)-1:
                text_data += '\n\r'
        return text_data

    def get_guilds(self):
        self.guilds = {}
        for guild in self.discord.get_guilds():
            self.guilds[guild['id']] = guild['name']

    def get(self):
        events = []
        aggregated_events = []
        text_data = ''
        for guild_id in self.guilds.keys():
            events.extend(self.discord.list_guild_events(guild_id))
        for server in config['SERVERS_EVENT']:
            r = requests.get(server + '/v1/events')
            if r.status_code != 200:
                print(f'Error {r.status_code}: {r.text}')
                continue
            if not r.text:
                continue
            _server_events = r.text.split('\n\r')
            server_events = [event.split('`') for event in _server_events]
            print(repr(server_events))
            aggregated_events.extend(
                [{'name': event[0], 'description': event[1], 'entity_metadata': {'location': event[2]}, 'scheduled_start_time': event[3], 'scheduled_end_time': event[4], 'guild_id': event[5]} for event in server_events]
            )
        aggregated_events.extend(events)
        aggregated_events.sort(key=lambda x: x['scheduled_start_time'])
        self.aggregated_events = self._format(aggregated_events)

        events = sorted(events, key=lambda d: d['scheduled_start_time'])
        self.events = self._format(events)

getData = GetData()

getData.get_guilds()
getData.get()

sched = BackgroundScheduler(daemon=True)
sched.add_job(getData.get,'interval',minutes=5)
sched.start()

app = Flask(__name__)

@app.route("/v1/events")
def get_data():
   return getData.events

@app.route("/v1/aggregated_events")
def get_aggregated_data():
    return getData.aggregated_events

@app.route("/")
def index():
    return "This API provide a list of events of NeosVR groups agragated by the USFN group. If you want to have your group listed or have any question please contact us at the USFN discord group (<a href='https://discord.gg/V3bXqm9j'>https://discord.gg/V3bXqm9j</a>). Source code available at <a href='https://github.com/brodokk/community_events.neos'>https://github.com/brodokk/community_events.neos</a>"