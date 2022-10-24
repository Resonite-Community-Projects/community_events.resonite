import re
import logging
import disnake
from disnake.ext import commands
from jsonschema import validate
import jsonschema

from ._base import Bot

class Apollo(Bot):
    jschema = {
            "$schema":"http://json-schema.org/draft-04/schema#",
            "title":"ApolloConfig",
            "description":"Config for Apollo",
            "type":"object",
            "properties":{
                "community_name": {
                    "description": "The name of the community",
                    "type": "string"
                },
                "community_url": {
                    "description": "The website of the community",
                    "type": "string"
                },
                "tags": {
                    "description": "A list of tags",
                    "type": "array"
                },
                "guild_id":{
                    "description":"The discord guild id of the community",
                    "type": "integer"
                },
                "guild_channel": {
                    "description": "The name of the channel",
                    "type": "string"
                },
                "bot":{
                    "description":"The bot id of the community",
                    "type": "integer"
                }
            },
            "required":[
                "community_name",
                "guild_id",
                "guild_channel",
                "bot"
            ]
        }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)
        self.guilds = {}
        for bot_config in getattr(config.BOTS, self.name, []):
            try:
                validate(instance=bot_config, schema=self.jschema)
            except jsonschema.exceptions.ValidationError as exc:
                logging.error(f"Invalid schema: {exc.message}")
                continue

            self.guilds[bot_config['guild_id']] = bot_config

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'{self.name} bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
        channel = disnake.utils.get(self.bot.get_all_channels(), guild__id=guild.guild_id, name=guild.guild_channel)
        _events_v1 = []
        _events_v2 = []
        async for msg in channel.history(limit=400, oldest_first=True):
            if msg.author.id == guild.bot:
                if not msg.embeds:
                    continue
                embed = msg.embeds[0]
                location = 'NeosVR'
                location_web_session_url = self.get_location_web_session_url(embed.description)
                location_session_url = self.get_location_session_url(embed.description)
                end_time = ''
                start_time = ''
                for field in embed.fields:
                    if field.name in ['Time']:
                        print(field.value)
                        r = re.search("<t:([0-9]{10}):F> - <t:([0-9]{10}):t>", field.value)
                        if r:
                            #print(r.groups())
                            start_time = r.group(1)
                            end_time = r.group(2)
                description = self._clean_text(embed.description)
                #print(embed.title, description, location)
                print(embed.title)
                if not end_time or not start_time or not self._filter_neos_event(
                    embed.title,
                    description,
                    location,
                ):
                    return
                event_v1 = self.sformat(
                    title = embed.title,
                    description = description,
                    location_str = location,
                    start_time = start_time,
                    end_time = end_time,
                    community_name = guild.community_name,
                    api_ver = 1
                )
                _events_v1.append(event_v1)
                event_v2 = self.sformat(
                    title = embed.title,
                    description = description,
                    session_image = session_image,
                    location_str = location,
                    location_web_session_url = location_web_session_url,
                    location_session_url = location_session_url,
                    start_time = start_time,
                    end_time = end_time,
                    community_name = guild.community_name,
                    community_url = '',
                    api_ver = 2
                )
                _events_v2.append(event_v2)
        self.rclient.write('events_v1', _events_v1, 1)
        self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, local_communities=self.bot.guilds)
        self.rclient.write('events_v2', _events_v2, 1)
        self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, local_communities=self.bot.guilds)

    async def get_data(self, dclient):
        print("update apollo events")
        return
        for guild_id, guild_data in self.guilds.items():
            await self.get_events(guild_data)