import datetime
from typing import List

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from google.oauth2 import service_account


class GoogleCalendarAPI:

    def __init__(self, calendar: str, credentials_file: str):
        self.calendar = calendar
        self.credentials_file = credentials_file
        self.service = self._get_calendar_service()
        self.google_calendars_id = self._get_google_calendars_id()

    def _get_calendar_service(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/calendar']
        )


        return build(serviceName='calendar', version='v3', credentials=credentials)

    def _get_google_calendars_id(self):
        calendars_result = self.service.calendarList().list(showHidden=True).execute()
        calendars = calendars_result.get('items', [])
        calendars_id = [calendar['id'] for calendar in calendars]
        return calendars_id

    def get_events(self):
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events = []
        if self.calendar not in self.google_calendars_id:
            self.service.calendarList().insert(
                body={'id': self.calendar}).execute()

        events_result = self.service.events().list(
            calendarId=self.calendar,
            timeMin=now, maxResults=10, singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result
