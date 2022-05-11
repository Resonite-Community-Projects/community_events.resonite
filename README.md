# community_event_neos

Small service for getting the events in multiple discord servers.

The token can be set directly in `config.yaml` file.

# Use

```
pip install -r requirements.txt
flask run
```

or if you want to use it directly with gunicorn

```
gunicorn -w 1 -b 0.0.0.0:5003 app:app
```

Note: For now you need to use only one worker since the requests to the API need to be start in only one thread for avoid rate limit problems

# Endpoints

- `/v1/events`: return the list of the event in an easy readable format for NeosVR: ```name`description`location`start_time`end_time`discord_name\n\r```
  Note: The last line don't have `\n\r`
- `/v1/aggregated_events`: same format as `/v1/events` but return the list of aggragated events from this instance with the ones from the instance listed in the config variable `SERVER_EVENTS`
- `/`: return a simple explanation of the utility of this API

Both endpoints `events` and `aggregated_events` have the possibility to have only some community
listed with the querystring `communities` who take as a parameters a list of community name
separated by a coma.
They also return a list of events from a Google calendar. See configuration below.

# Add a google agenda

For adding a google agenda you need:

- create a Google calendar with your personal account
- create, or use, a Google Cloud Plateform account and create a new project. Enable the calendar API on it and create a `Service Account` with a `json` API key. Then you need to add the email of this Service Account API key as an authorized user of your personal Google calendar.
- Copy the `json` file next to the project or where you want on the system.
- Update the `config.toml` configuration depending on your need.

Note: The id of the calendar is in the settings of your Google Calendar under calendar integration.