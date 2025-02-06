# Usage

The system is splited in different instances.

The first one will handle all the signals while the other will handle the clients, the HTTP API and the Website.

!!! danger

    All commands must be run in the folder `backend`.

!!! note

    As seen in the [configuration section](server-configuration.md) since the HTTP API require you to use `resonite-communities.local` for local development all link will use this, per convention.

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

Accessible at [http://resonite-communities.local:8000/](http://resonite-communities.local:8000/) and [http://private.resonite-communities.local:8000/](http://private.resonite-communities.local:8000/). See the [HTTP API section for more information](../ClientIntegration/http-api-usage.md).

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the HTTP API client will listen

## Website

To start an instance of the web client use:

```console
poetry run web_client
```

Accessible at [http://resonite-communities.local:8001/](http://resonite-communities.local:8001/).

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the Website client will listen

## Documentation

To start an instance of the documentation use:

```console
poetry run docs serve
```

Accessible at [http://resonite-communities.local:8002](http://resonite-communities.local:8002)

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the Documentation will listen
