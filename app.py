import json
import requests
import time
import toml

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask
from flask import jsonify

class DiscordEvents:

    def __init__(self, discord_token: str) -> None:
        self.base_api_url = 'https://discord.com/api/v8'
        self.auth_headers = {
            'Authorization':f'Bot {discord_token}',
            'User-Agent':'DiscordBot (https://your.bot/url) Python/3.9 aiohttp/3.8.1',
            'Content-Type':'application/json'
        }
        self.session = requests.session()

    def list_guild_events(self, guild_id) -> list:
        event_retrieve_url = f'{self.base_api_url}/guilds/{guild_id}/scheduled-events'
        with self.session as session:
            try:
                with session.get(event_retrieve_url, headers=self.auth_headers) as response:
                    response.raise_for_status()
                    assert response.status_code == 200
                    response_list = response.json()
                    return response_list
            except Exception as e:
                if '429' in str(e):
                    print(f"Rate limit exceeded. Try again in {self.headers['X-RateLimit-Reset-After']} seconds.")
                print(f'EXCEPTION: {e}')
            finally:
                session.close()


with open('config.toml', 'r') as f:
    config = toml.load(f)

DISCORD_BOT_TOKEN = config['DISCORD_BOT_TOKEN']


class GetData:
    guild_ids = ['819234726404816907']
    text_data = ""
    discordEvent = DiscordEvents(DISCORD_BOT_TOKEN)

    def get(self):
        text_data = ''
        guild_ids = self.guild_ids
        for guild_id in guild_ids:
            events = self.discordEvent.list_guild_events(guild_id)
            for index, event in enumerate(events):
                text_data += f"{event['name']}`{event['entity_metadata']['location']}`{event['scheduled_start_time']}`{event['scheduled_end_time']}"
                if index != len(events)-1:
                    text_data += '\n\r'
        self.text_data = text_data



getData = GetData()

sched = BackgroundScheduler(daemon=True)
sched.add_job(getData.get,'interval',minutes=5)
sched.start()


class MyFlaskApp(Flask):
  def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
    getData.get()
    super(MyFlaskApp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = MyFlaskApp(__name__)
app.run()

@app.route("/v1/events")
def get_data():
   return getData.text_data

if __name__ == "__main__":
    app.run()