# community_event.resonite

Service for announcing Resonite events and stream from multiple source like Discord and Google Agenda on client like Resonite and Web Browsers.

You can check [resonite communities website](https://resonite-communities.com) for the running instance.

See the [documentation](https://docs.resonite-communities.com) to get started.

To help the development see about the [documentation architecture](https://docs.resonite-communities.com/DeveloperGuide/architecture/) as well as the API.

To build the documentation locally simply use the following commands (keep in mind you need Python 3.12.* as well as poetry installed in some way in your Operating System):

```
poetry install
poetry run mkdocs serve -a 0.0.0.0:8002 # We use the port 8002 because during development the port 8000 and 8001 are reserved
```

And then check [http://localhost:8002](http://localhost:8002)