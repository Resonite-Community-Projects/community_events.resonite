# HTTP API usage

!!! construction "This need to be documented"

## Endpoints

### V1

**Note**: This endpoint is noted as deprecated

- `/v1/events`: return the list of the event in an easy readable format for Resonite: ```name`description`location`start_time`end_time`community_name\n\r```
  Note: The last line don't have `\n\r`
- `/v1/aggregated_events`: same format as `/v1/events` but return the list of aggragated events from this instance with the ones from the instance listed in the config variable `SERVER_EVENTS`
- `/`: WebUI client

Both endpoints `events` and `aggregated_events` have the possibility to have only some community
listed with the querystring `communities` who take as a parameters a list of community name
separated by a coma.
They also return a list of events from a Google calendar. See configuration below.

### V2

- `/v2/communities`: return the list of the communities available on this event server
  `/v2/events`: return the list of the event in an easy readable format for Resonite: ```\n\r```
  Note: The last line don't have `\n\r`
- `/v2/aggregated_events`: same format as `/v2/events` but return the list of aggragated events from this instance with the ones from the instance listed in the config variable `SERVER_EVENTS`
- `/`: WebUI client