import json
import requests
import time
import toml

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask import jsonify

class Discord:

    def __init__(self, discord_token: str) -> None:
        self.base_api_url = 'https://discord.com/api/v8'
        self.auth_headers = {
            'Authorization':f'Bot {discord_token}',
            'User-Agent':'DiscordBot (https://your.bot/url) Python/3.9 aiohttp/3.8.1',
            'Content-Type':'application/json'
        }
        self.session = requests.session()
    
    def _request(self, method, url, headers=None, data=None) -> requests.Response:
        if not headers:
            headers = self.auth_headers
        with self.session as session:
            try:
                print(f'{method} {url}')
                with session.request(method, url, headers=headers, data=data) as response:
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                if '429' in str(e):
                    print(f"Rate limit exceeded when requesting discord API")
                    print(f"Trying again in {response.headers['X-RateLimit-Reset-After']} seconds")
                    time.sleep(float(response.headers['X-RateLimit-Reset-After']) + 1 )
                    return self._request(method, url, headers=headers, data=data)
                print(f'EXCEPTION: {e}')
            finally:
                session.close()

    def get_guilds(self) -> dict:
        return self._request('GET', f'{self.base_api_url}/users/@me/guilds')

    def list_guild_events(self, guild_id) -> list:
        return self._request('GET', f'{self.base_api_url}/guilds/{guild_id}/scheduled-events')

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
            text_data += f"{event['name']}`{event['entity_metadata']['location']}`{event['scheduled_start_timeiiii']}`{event['scheduled_end_time']}`{self.guilds[event['guild_id']]}"
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