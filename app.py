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
    text_data = ""
    discord = Discord(DISCORD_BOT_TOKEN)

    def get_guilds(self):
        for guild in self.discord.get_guilds():
            self.guilds[guild['id']] = guild['name']

    def get(self):
        events = []
        text_data = ''
        for guild_id in self.guilds.keys():
            events.extend(self.discord.list_guild_events(guild_id))
        events = sorted(events, key=lambda d: d['scheduled_start_time'])
        for index, event in enumerate(events):
            text_data += f"{event['name']}`{event['entity_metadata']['location']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}`{self.guilds[event['guild_id']]}"
            if index != len(events)-1:
                text_data += '\n\r'
        self.text_data = text_data

getData = GetData()

getData.get_guilds()
getData.get()

sched = BackgroundScheduler(daemon=True)
sched.add_job(getData.get,'interval',minutes=5)
sched.start()

app = Flask(__name__)

@app.route("/v1/events")
def get_data():
   return getData.text_data

@app.route("/")
def index():
    return "This API provide a list of events of NeosVR groups agragated by the USFN group. If you want to have your group listed or have any question please contact us at the USFN discord group (<a href='https://discord.gg/V3bXqm9j'>https://discord.gg/V3bXqm9j</a>). Source code available at <a href='https://github.com/brodokk/community_events.neos'>https://github.com/brodokk/community_events.neos</a>"