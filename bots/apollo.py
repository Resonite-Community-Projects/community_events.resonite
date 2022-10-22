import re
import disnake
from disnake.ext import commands

from ._base import Bot

re_world_session_web_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_world_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')

class Apollo(Bot):

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

    @commands.Cog.listener()
    async def on_ready(self):
        print('Apollo bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=5)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
        try:
            channel = disnake.utils.get(self.bot.get_all_channels(), guild__id=guild.id, name=self.config.GUILDS[str(guild.id)]['channel'])
        except AttributeError:
            return
        _events_v1 = []
        _events_v2 = []
        async for msg in channel.history(limit=400, oldest_first=True):
            if msg.author.id == self.config.GUILDS[str(guild.id)]['bot']:
                if not msg.embeds:
                    continue
                embed = msg.embeds[0]
                location = 'NeosVR'
                world_session_web_url = ''
                world_session_web_url_match = re.search(re_world_session_web_url_match_compiled, embed.description)
                if world_session_web_url_match:
                    world_session_web_url = world_session_web_url_match.group()
                world_session_url = ''
                world_session_url_match = re.search(re_world_session_url_match_compiled, embed.description)
                if world_session_url_match:
                    world_session_url = world_session_url_match.group()
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
                    community_name = guild.name,
                    api_ver = 1
                )
                _events_v1.append(event_v1)
                event_v2 = self.sformat(
                    title = embed.title,
                    description = description,
                    location_str = location,
                    location_web_url = world_session_web_url,
                    location_session_url = world_session_url,
                    start_time = start_time,
                    end_time = end_time,
                    community_name = guild.name,
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
        for guild in self.bot.guilds:
            await self.get_events(guild)
