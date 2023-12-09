from .external import ExternalEventsCollector
from .discord import DiscordEventsCollector
from .google import GoogleCalendarEventsCollector
from .apollo import ApolloEventsCollector

__all__ = [external, discord, google, apollo]