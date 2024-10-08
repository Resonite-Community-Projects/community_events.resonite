from ._base import EventsCollector

from resonite_communities.signals import SignalSchedulerType


class ExternalEventsCollector(EventsCollector):
    scheduler_type = SignalSchedulerType.APSCHEDULER
    jschema = {
            "$schema":"http://json-schema.org/draft-04/schema#",
            "title":"ApolloConfig",
            "description":"Config for Apollo",
            "type":"object",
            "properties":{},
            #"required":[]
        }

    def __init__(self, config, scheduler):
        super().__init__(config, scheduler)

    def collect(self):
        self.logger.info('Update events collector from external source')
