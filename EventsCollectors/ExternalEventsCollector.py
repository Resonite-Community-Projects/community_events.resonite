import re
from time import sleep

import disnake
from disnake.ext import commands
from ._base import EventsCollector, separator, ekey


class ExternalEventsCollector(EventsCollector):
    jschema = {
            "$schema":"http://json-schema.org/draft-04/schema#",
            "title":"ApolloConfig",
            "description":"Config for Apollo",
            "type":"object",
            "properties":{},
            "required":[]
        }

    def __init__(self, bot, config, sched, dclient, rclient):
        super().__init__(bot, config, sched, dclient, rclient)

    async def get_events(self):
        external_communities = self.get_external_communities()
        external_communities.extend(self.communities_name)

        _event_v1 = self.rclient.get('events_v1')
        _event_v1 = _event_v1.decode("utf-8").split(separator[1]['event'])

        _aggregated_events_v1 = self.get_aggregated_events(api_ver=1)
        _aggregated_events_v1.extend(_event_v1)
        self.rclient.write('aggregated_events_v1', _aggregated_events_v1, api_ver=1, current_communities=external_communities)

        _event_v2 = self.rclient.get('events_v2')
        _event_v2 = _event_v2.decode("utf-8").split(separator[2]['event'])

        _aggregated_events_v2 = self.get_aggregated_events(api_ver=2)
        _aggregated_events_v2.extend(_event_v2)
        self.rclient.write('aggregated_events_v2', _aggregated_events_v2, api_ver=2, current_communities=external_communities)

    async def get_data(self, dclient):
        self.logger.info(f'Update {self.name} events collector')
        await self.get_events()
