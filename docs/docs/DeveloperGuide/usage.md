---
title: Usage
prev: DeveloperGuide/installation.md
next: DeveloperGuide/migrations.md
---

The system is splited in different instances.

The first one will handle all the signals while the other will handle the clients, the HTTP API and the Website.

!!! danger

    All commands must be run in the folder `backend`.

!!! note

    As seen in the [configuration section](server-configuration.md) since the HTTP API require you to use `resonite-communities.local` for local development all link will use this, per convention.

## Running the System

The Resonite Community Events system is composed of several independent services. For local development, you can run these services individually using Poetry, or collectively using Docker Compose profiles.

!!! danger "Run Commands from `backend` Directory"
    All `poetry run` commands must be executed from the `backend` directory of the project. For example: `cd backend && poetry run signals_manager`.

### Docker Compose Profiles Overview

Our Docker Compose setup utilizes `profiles` to group related services. This allows you to start only the components you need for a specific development task, saving resources.

*   **`database`**: Contains the PostgreSQL database service. Essential for all other services.
*   **`manager`**: Includes the `signals_manager` service, responsible for collecting and transmitting signals.
*   **`clients`**: Includes the `api_client` (HTTP API) and `web_client` (Website) services.

You can run the entire Docker Compose stack with:

```console
docker compose --profile "*" up -d
```

Or, you can select specific profiles. For example, to run only the database and the signals manager:

```console
docker compose --profile database --profile manager up -d
```

### Running Services Individually (without Docker Compose)

If you prefer to run services directly on your host machine (after following the [Local Development without Docker stack](installation.md#local-development-without-docker-stack) guide), use the following commands:

#### Signals Manager

The `signals_manager` handles collectors and transmitters, running them on a schedule (default 5 minutes). See the [Architecture section](architecture.md) for more information.

To start an instance of the signals manager:

```console
poetry run signals_manager
```

#### HTTP API

The `api_client` serves requests from any client in either JSON or TEXT format.

To start an instance of the HTTP API client:

```console
poetry run api_client
```

Accessible at [http://resonite-communities.local:8000/](http://resonite-communities.local:8000/) and [http://private.resonite-communities.local:8000/](http://private.resonite-communities.local:8000/). See the [HTTP API section for more information](../ClientIntegration/http-api-usage.md).

!!! tip "Change Host and Port"
    You can use the option `-a <IP:PORT>` to change the host and port the HTTP API client will listen on. For example: `poetry run api_client -a 0.0.0.0:8080`.

#### Web Client

The `web_client` serves the project's website.

To start an instance of the web client:

```console
poetry run web_client
```

Accessible at [http://resonite-communities.local:8001/](http://resonite-communities.local:8001/).

!!! tip "Change Host and Port"
    You can use the option `-a <IP:PORT>` to change the host and port the Website client will listen on. For example: `poetry run web_client -a 0.0.0.0:8081`.

#### Documentation

To start a local instance of the documentation website:

```console
poetry run docs serve
```

Accessible at [http://resonite-communities.local:8002](http://resonite-communities.local:8002).

!!! tip "Change Host and Port"
    You can use the option `-a <IP:PORT>` to change the host and port the Documentation will listen on. For example: `poetry run docs serve -a 0.0.0.0:8082`.

## Development Tips

### Developing on another device where Resonite is running

If you are developing on a different device than where Resonite is running, you might need to configure VSCode to listen on all network interfaces.

1.  In VSCode, open **Settings** (`Ctrl+,` or `Cmd+,`).
2.  Search for `Remote: Local Port Host`.
3.  Set this option to `allInterfaces`.

### Direct connection without port (e.g., `resonite-communities.local` instead of `resonite-communities.local:8000`)

If you've configured your hosts file as explained in [Server Configuration](../deployment/server-configuration.md) and want to access services without specifying the port (e.g., `http://resonite-communities.local` instead of `http://resonite-communities.local:8000`), you'll need to redirect traffic from port 80 to the forwarded address provided by VSCode.

1.  In VSCode, go to the **PORTS** forwarding settings.
2.  Note the "Forwarded Address" port for the service you want to access (e.g., 44677).

#### Linux

On Linux, you can use `socat` to redirect traffic. Replace `<FORWARDED_ADDRESS_PORT>` with the actual port from VSCode.

```console
sudo socat TCP-LISTEN:80,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:<FORWARDED_ADDRESS_PORT>
```

!!! danger "Local Only"
    This `socat` setup only works locally. While `http://resonite-communities.local:8001` might work from a remote device, `http://resonite-communities.local` will not.

#### Windows

On Windows, you can use the built-in `netsh` command to forward ports. You will need to run this in an administrator command prompt. Replace `<FORWARDED_ADDRESS_PORT>` with the actual port from VSCode.

```console
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=<FORWARDED_ADDRESS_PORT> connectaddress=127.0.0.1
```

To remove the rule:

```console
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0
```
