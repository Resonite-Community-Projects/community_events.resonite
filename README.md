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

- `/v1/events`: return the list of the event in an easy readable format for NeosVR: ```name`location`start_time`end_time`discord_name\n\r```
  Note: The last line don't have `\n\r`
- `/`: return a simple explanation of the utility of this API

# Utilities

The script `get_discord_server_list.py` return the list where the bot is present.