# Usage

The system is splited in different instances.

The first one will handle all the signals while the other will handle the clients, the HTTP API and the Website.

!!! danger

    All commands must be run in the folder `backend`.

## Signals manager

By default the system will run it's signals (both collectors and transmitters) at
at an interval of 5 minutes. See the [section about the architecture of the system](architecture.md)
for more information.

To start an instance of the signals manager use:

```console
poetry run signals_manager
```

## HTTP API

To start an instance of the HTTP API client use:

```console
poetry run api_client
```

Accessible at [http://localhost:8000/](http://localhost:8000/).

## Website

To start an instance of the web client use:

```console
poetry run web_client
```

Accessible at [http://localhost:8001/](http://localhost:8001/).


## Documentation

To start an instance of the documentation use:

```console
poetry run mkdocs serve -a 0.0.0.0:800
```

Accessible at [http://localhost:8002](http://localhost:8002)