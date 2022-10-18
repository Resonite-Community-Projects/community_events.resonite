import os
import toml
import pytz
from dateutil.parser import parse

from disnake.ext import commands

from .utils.google import GoogleCalendarAPI

with open('config.toml', 'r') as f:
    config = toml.load(f)

CALENDARS_ACCEPTED = config['CALENDARS_ACCEPTED']
CREDENTIALS_FILE = config['CREDENTIALS_FILE']

class GoogleCalendar(commands.Cog):

    def __init__(self, bot, config, sched, dclient, rclient):
        print('initialize google bot')
        self.bot = bot
        self.config = config
        self.sched = sched
        self.dclient = dclient
        self.rclient = rclient

        if CREDENTIALS_FILE:
            self.google = GoogleCalendarAPI(CALENDARS_ACCEPTED, CREDENTIALS_FILE)
        else:
            print("No credential found ignoring google event update")

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

    @commands.Cog.listener()
    async def on_ready(self):
        if CREDENTIALS_FILE:
            print('google bot ready')
            self.sched.add_job(self.get_data, 'interval', args=(self.dclient,), minutes=5)
            await self.get_data(self.dclient)

    async def get_data(self, dclient):
        print('update google events')
        google_data = self.google.get_events()
        google_event = []
        for event in google_data[0]['items']:
            community, name = event['summary'].split('`')
            start_time = self.parse_date(event['start'])
            end_time = self.parse_date(event['end'])
            location = event['location']
            description = ''
            if 'description' in event:
                description = self.clean_google_description(event['description'])
            event_v1 = "{}`{}`{}`{}`{}`{}".format(
                name,
                description,
                location,
                start_time,
                end_time,
                community
            )
            google_event.append(event_v1)
        self.rclient.write('events_v1', google_event, 1)