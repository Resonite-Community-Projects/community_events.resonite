from disnake.ext import commands

from ._base import EventsCollector

class DiscordEventsCollector(EventsCollector, commands.Cog):
    signal_type = 'discord'
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
                }
            },
            "required":[
                "community_name",
                "community_url",
                "tags",
                "guild_id"
            ]
        }

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

        self.guilds = {}

        if not self.valid_config:
            return

        for bot_config in getattr(self.config.SIGNALS, self.name, []):
            self.guilds[bot_config['guild_id']] = bot_config

    @commands.Cog.listener()
    async def on_ready(self):
        self.init_scheduler()