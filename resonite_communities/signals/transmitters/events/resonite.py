import json
import struct
import datetime
import random
import string
import logging
from dateutil import parser

from resonitepy.client import Client
from resonitepy.classes import LoginDetails

def fromDateTimeComp(value):

    dt_byte_1 = ord(value[0])
    dt_byte_2 = ord(value[1])
    dt_shifted_byte_2 = dt_byte_2 << 15
    dt = dt_byte_1 | dt_shifted_byte_2
    dt = 60 * dt
    return datetime.datetime.fromtimestamp(dt)

def from2DateTimeComp(value):
    return fromDateTimeComp(value[0:2]), fromDateTimeComp(value[2:4])

def toDateTimeComp(value):

    dt_timestamp = int(value.timestamp())
    dt_timestamp = dt_timestamp // 60

    dt_byte_1 = chr(dt_timestamp & 32767)
    dt_byte_2 = chr(dt_timestamp >> 15)

    return dt_byte_1 + dt_byte_2

def to2DateTimeComp(dt1, dt2):
    return toDateTimeComp(dt1) + toDateTimeComp(dt2)

def generated_random_id(other_ids):
    while True:
        id = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(3))
        if id not in other_ids:
            return id

def new_event(start_date, end_date, title, description, other_ids):
    return {
        generated_random_id(other_ids): {
            'DT': to2DateTimeComp(start_date, end_date),
            'T1': title,
            'T2': description
        }
    }

separator = {
    'field': chr(30),
    'event': chr(29),
}

class ResoniteCalendarTransmitter:

    def __init__(self, config, sched, rclient, *args, **kwargs):
        self.name = self.__class__.__name__

        self.config = config
        self.sched = sched
        self.rclient = rclient
        self.logger = logging.getLogger('community_events')
        self.nclient = Client()

        self.nclient.login(
            LoginDetails(
                ownerId=self.config.CLOUDVAR_RESONITE_USER,
                password=self.config.CLOUDVAR_RESONITE_PASS
            )
        )

        self._initialise_scheduler()

    def _initialise_scheduler(self):
        self.logger.info(f'{self.name} events transmitter ready')
        self.sched.add_job(self.transmitt,'interval', args=(self.rclient,), minutes=1)
        self.transmitt(self.rclient)

    def transmitt(self, rclient):
        aggregated_events_v2 = self.rclient.get('aggregated_events_v2')
        events = aggregated_events_v2.decode("utf-8").split(separator['event'])
        cloud = json.loads('{"Meta":{"Name":"TestCommunityEvents.All","Desc":"","Color":"","LastEdited":""},"Events":{}}')
        for event in events:
            event = event.split(separator['field'])
            try:
                cloud['Events'].update(
                    new_event(
                        start_date=parser.parse(event[6]),
                        end_date=parser.parse(event[7]),
                        title=event[0],
                        description=event[1],
                        other_ids=cloud['Events'].keys()
                    )
                )
            except IndexError:
                logging.error('Invalid event format')

        cloud_var = f'{self.config.CLOUDVAR_RESONITE_USER}.{self.config.CLOUDVAR_BASE_NAME}.{self.config.CLOUDVAR_GENERAL_NAME}'
        setCloudVar = self.nclient.setCloudVar(
            self.config.CLOUDVAR_RESONITE_USER,
            cloud_var,
            json.dumps(cloud, ensure_ascii=False)
        )

        self.logger.info(f'Events transmitted to Resonite {cloud_var} cloud var')

