import re
import disnake
from disnake.ext import commands

GUILD = {
            819234726404816907: {
                'channel': 'test-apollo',
                'bot': 475744554910351370
            }
        }

re_world_session_web_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_world_session_url_match_compiled = re.compile('(lnl-nat|neos-steam):\/\/([^\s]+)')

class Apollo(commands.Cog):

    def __init__(self, bot, config, sched, dclient, rclient):
        print('initialise Apollo bot')
        self.bot = bot
        self.config = config
        self.sched = sched
        self.dclient = dclient
        self.rclient = rclient

    @commands.Cog.listener()
    async def on_ready(self):
        print('Apollo bot ready')
        self.sched.add_job(self.get_data,'interval', args=(self.dclient,), minutes=1)
        await self.get_data(self.dclient)

    async def get_events(self, guild):
        channel = disnake.utils.get(self.bot.get_all_channels(), guild__id=guild.id, name=GUILD[guild.id]['channel'])
        async for msg in channel.history(limit=200):
            if msg.author.id == GUILD[guild.id]['bot']:
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
                        r = re.search("<t:([0-9]{10}):F> - <t:([0-9]{10}):t>", field.value)
                        if r:
                            start_time = r.group(1)
                            end_time = r.group(2)
                event_v1 = "{}`{}`{}`{}`{}`{}".format(
                    guild.name,
                    embed.title,
                    embed.description,
                    location,
                    start_time,
                    end_time,
                )
                #print(event_v1)
                event_v2 = "{}`{}`{}`{}`{}`{}`{}`{}".format(
                    embed.title,
                    embed.description,
                    location,
                    world_session_web_url,
                    world_session_url,
                    start_time,
                    end_time,
                    guild.name,
                )
                #print(event_v2)

    async def get_data(self, dclient):
        print("update apollo events")
        for guild in self.bot.guilds:
            await self.get_events(guild)
