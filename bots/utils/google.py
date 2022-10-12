import datetime
from typing import List

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from google.oauth2 import service_account


class GoogleCalendarAPI:

    def __init__(self, calendars_accepted: List[str], credentials_file: str):
        self.calendars_accepted = calendars_accepted
        self.credentials_file = credentials_file
        self.service = self._get_calendar_service()
        self.google_calendars_id = self._get_google_calendars_id()

    def _get_calendar_service(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=['https://www.googleapis.com/auth/calendar'])
        except FileNotFoundError:
            raise RuntimeError("credentials.json file not found, download it from google")

        return build(serviceName='calendar', version='v3', credentials=credentials)

    def _get_google_calendars_id(self):
        calendars_result = self.service.calendarList().list(showHidden=True).execute()
        calendars = calendars_result.get('items', [])
        calendars_id = [calendar['id'] for calendar in calendars]
        return calendars_id

    def get_events(self):
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events = []
        for calendar_id in self.calendars_accepted:
            if calendar_id not in self.google_calendars_id:
                service.calendarList().insert(
                    body={'id': calendar_id}).execute()

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now, maxResults=10, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events.append(events_result)
        return events
