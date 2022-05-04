import json
import time

import requests

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
                raise e
            finally:
                session.close()

    def get_guilds(self) -> dict:
        return self._request('GET', f'{self.base_api_url}/users/@me/guilds')

    def list_guild_events(self, guild_id) -> list:
        return self._request('GET', f'{self.base_api_url}/guilds/{guild_id}/scheduled-events')

