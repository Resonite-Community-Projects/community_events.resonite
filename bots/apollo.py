import re
import logging
from datetime import datetime
import disnake
from disnake.ext import commands

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
                "community_description": {
                    "description": "The description of a community",
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
                "community_description",
                "community_url",
                "tags",
                "guild_id",
                "guild_channel",
                "bot"
            ]
        }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

        self.older_communities = self.communities_name
        for bot_config in getattr(self.config.BOTS, self.name, []):
            self.guilds[bot_config['guild_id']] = bot_config
            self.update_communities(bot_config.community_name)
            self.older_communities = [x for x in self.older_communities if x != bot_config.community_name]

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info(f'{self.name} bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
        channel = disnake.utils.get(self.bot.get_all_channels(), guild__id=guild.guild_id, name=guild.guild_channel)
        _events_v1 = []
        _events_v2 = []
        async for msg in channel.history(limit=3):
            if msg.author.id == guild.bot:
                if not msg.embeds:
                    continue
                embed = msg.embeds[0]
                location_str = self.get_location_str(embed.description)
                location_web_session_url = self.get_location_web_session_url(embed.description)
                location_session_url = self.get_location_session_url(embed.description)
                tags = "`".join(guild.tags)
                community_url = guild.community_url
                end_time = ''
                start_time = ''
                for field in embed.fields:
                    if field.name in ['Time']:
                        r = re.search("<t:([0-9]{10}):F> - <t:([0-9]{10}):t>", field.value)
                        if r:
                            start_time = datetime.fromtimestamp(int(r.group(1)))
                            end_time = datetime.fromtimestamp(int(r.group(2)))
                if not end_time or not start_time or not self._filter_neos_event(
                    embed.title,
                    embed.description,
                    location_str,
                ):
                    return
                event_v1 = self.sformat(
                    title = embed.title,
                    description = self._clean_text(event.description),
                    location_str = location_str,
                    start_time = start_time,
                    end_time = end_time,
                    community_name = guild.community_name,
                    api_ver = 1
                )
                _events_v1.append(event_v1)
                event_v2 = self.sformat(
                    title = embed.title,
                    description = embed.description,
                    session_image = '',
                    location_str = location_str,
                    location_web_session_url = location_web_session_url,
                    location_session_url = location_session_url,
                    start_time = start_time,
                    end_time = end_time,
                    community_name = guild.community_name,
                    community_url = community_url,
                    tags = tags,
                    api_ver = 2
                )
                _events_v2.append(event_v2)
        self.rclient.write('events_v1', _events_v1,  api_ver=1, older_communities=self.older_communities)
        self.rclient.write('events_v2', _events_v2, api_ver=2, older_communities=self.older_communities)

        _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
        if _aggregated_events_v1:
            _events_v1.extend(_aggregated_events_v1)
        self.rclient.write('aggregated_events_v1', _events_v1, api_ver=1, older_communities=self.older_communities)

        _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
        if _aggregated_events_v2:
            _events_v2.extend(_aggregated_events_v2)
        self.rclient.write('aggregated_events_v2', _events_v2, api_ver=2, older_communities=self.older_communities)

    async def get_data(self, dclient):
        print("update apollo events")
        for guild_id, guild_data in self.guilds.items():
            await self.get_events(guild_data)