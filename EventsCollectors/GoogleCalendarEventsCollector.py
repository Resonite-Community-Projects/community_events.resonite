import os
import toml
import pytz
from dateutil.parser import parse

from disnake.ext import commands

from .utils.google import GoogleCalendarAPI
from ._base import EventsCollector


class GoogleCalendarEventsCollector(EventsCollector):
    jschema = {
        "$schema":"http://json-schema.org/draft-04/schema#",
        "title":"GoogleCalendarConfig",
        "description":"Config for GoogleCalendar",
        "type":"object",
        "properties":{
            "communities_name": {
                "description": "",
                "type": "array"
            },
            "email":{
                "description":"The email of the calendar to get events from",
                "type": "string"
            },
            "credentials_file":{
                "description":"The credential file of the calendar",
                "type": "string"
            }
        },
        "required":[
            "communities_name",
            "email",
            "credentials_file"
        ]
    }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

        if not self.valide_config:
            return

        self.clients = []

        for bot_config in getattr(self.config.BOTS, self.name, []):
            try:
                self.clients.append(GoogleCalendarAPI(bot_config))
            except FileNotFoundError:
                self.logger.error(f"Ignore {self.name} for now. Google {bot_config.credentials_file} not found.")
                continue

            for community_name in bot_config.communities_name:
                self.update_communities(community_name)

        self.init_sched()

    def parse_date(self, date):
        """ Parse data."""
        if 'date' in date:
            date = parse(date['date'])
            return date.replace(tzinfo=pytz.UTC).isoformat()
        else:
            date = date['dateTime']
            return parse(date).isoformat()

    def clean_google_description(self, description):
        """ Clean description from google. """
        description = description.replace('<span>', ' ')
        description = description.replace('</span>', ' ')
        description = description.replace('<html-blob>', ' ')
        description = description.replace('</html-blob>', ' ')
        description = description.strip(' ')
        return description

    def format_event(self, event, api_ver):
        community_name, name = event['summary'].split('`')
        start_time = self.parse_date(event['start'])
        end_time = self.parse_date(event['end'])
        location = event['location']
        location_web_session_url = ''
        location_session_url = ''
        description = ''
        if 'description' in event:
            description = self.clean_google_description(event['description'])
            location_web_session_url = self.get_location_web_session_url(event['description'])
            location_session_url = self.get_location_session_url(event['description'])
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
                community_url = "",
                api_ver = 2
            )
        return event

    def get_data(self, dclient):
        self.logger.info(f'Update {self.name} events collector')
        for client in self.clients:
            google_data = client.get_events()
            _events_v1 = []
            _events_v2 = []
            for event in google_data['items']:
                _events_v1.append(self.format_event(event, api_ver=1))
                _events_v2.append(self.format_event(event, api_ver=2))

            self.rclient.write('events_v1', _events_v1, api_ver=1, current_communities=client.bot_config.communities_name)
            self.rclient.write('events_v2', _events_v2, api_ver=2, current_communities=client.bot_config.communities_name)