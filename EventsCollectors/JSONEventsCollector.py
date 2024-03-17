import os
import toml
import requests
import json
from dateutil.parser import parse

from disnake.ext import commands

from ._base import EventsCollector


class JSONEventsCollector(EventsCollector):
    jschema = {
        "$schema":"http://json-schema.org/draft-04/schema#",
        "title":"JsonEventsConfig",
        "description":"Config for JSON collector",
        "type":"object",
        "properties":{
            "community_name": {
                "description": "The name of the community",
                "type": "string"
            },
            "community_description": {
                "description": "The description of the community",
                "type": "string"
            },
            "events_url":{
                "description":"The URL to get events from",
                "type": "string"
            },
            "tags":{
                "description":"A list of tags",
                "type": "array"
            }
        },
        "required":[
            "community_name",
            "events_url",
        ]
    }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

        if not self.valide_config:
            return

        for bot_config in getattr(self.config.BOTS, self.name, []):
            self.logger.info(f"Bot config: {bot_config}")

    def format_event(self, event, api_ver, community_name, community_tags):
        name = event['name']
        community_name = community_name
        start_time = event['start_time']
        end_time = event['end_time']
        location = event['location']
        location_web_session_url = ''
        location_session_url = ''
        tags = "`".join(community_tags)
        description = event['description']
        if api_ver == 1:
            event = self.sformat(
                title = name,
                description = description,
                location_str = location,
                start_time = start_time,
                end_time = end_time,
                community_name = community_name,
                api_ver = 1
            )
        if api_ver == 2:
            session_image = ''
            event = self.sformat(
                title = name,
                description = description,
                session_image = session_image,
                location_str = location,
                location_web_session_url = location_web_session_url,
                location_session_url = location_session_url,
                start_time = start_time,
                end_time = end_time,
                community_name = community_name,
                tags = tags,
                community_url = "",
                api_ver = 2
            )
        return event

    def get_data(self, dclient):
        self.logger.info(f'Update {self.name} events collector')

        for bot_config in getattr(self.config.BOTS, self.name, []):

            community_name = bot_config['community_name']

            try:
                community_tags = bot_config['tags']
            except KeyError:
                community_tags = []

            self.logger.info(f"Processing events for {community_name} with events_url {bot_config['events_url']}")

            try:
                response = requests.get(
                    bot_config['events_url']
                )
            except:
                self.logger.error(f"Exception on request for {community_name}")
                continue

            if response.status_code != 200:
                self.logger.error(f"Got {response.status_code} from {community_name}, expecting 200. Skipping")
                continue

            events_json = json.loads(response.text)

            _events_v1 = []
            _events_v2 = []

            for event in events_json:
                _events_v1.append(self.format_event(event, api_ver=1, community_name=community_name, community_tags=community_tags))
                _events_v2.append(self.format_event(event, api_ver=2, community_name=community_name, community_tags=community_tags))

            self.rclient.write('events_v1', _events_v1, api_ver=1, current_communities=community_name)
            self.rclient.write('events_v2', _events_v2, api_ver=2, current_communities=community_name)