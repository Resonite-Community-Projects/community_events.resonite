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