# community_event.resonite

> [!WARNING]  
> Refactor in progress, please look at the stable branch

Service for announcing Resonite events and stream from multiple source like Discord and Google Agenda on client like Resonite and Web Browsers.

This tool has been write in a way that different communities can host their own server and can be connected to
each other. There is a main instance available at [resonite-community.events](https://resonite-community.events).

To setup the project see the [documentation](http://localhost:8001/DeveloperGuide/installation/) about getting started.

To help the development see about the [architecture](http://localhost:8001/DeveloperGuide/architecture/) as well as the API.

To build the documentation locally simply use the following commands (keep in mind you need Python 3.12.* as well as poetry installed in some way in your Operating System):

```
poetry install
poetry run mkdocs serve -a 0.0.0.0:8002 # We use the port 8002 because during development the port 8000 and 8001 are already occupied
```

And then check [http://localhost:8002](http://localhost:8002)