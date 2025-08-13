---
title: Installation
prev: DeveloperGuide/deployment/requirements.md
next: DeveloperGuide/deployment/configuration.md
---


!!! Info

    This is a simple explanation of our current stack is configured for you to do the same if you ever want to run your own server for your own community.

!!! info

    During the development you only need tu run the database but while we explain everything here, a fully working docker compose example file is available at the root of the project.

    You **don't need** to create your own based on this instruction as this is an explanation from the already exist docker compose file. But use the command as needed.

We use docker compose `profiles` to separate each components in groups: `database`, `manager` and `clients`.

About the `config.toml` please see the section [Server Configuration](server-configuration.md).

!!! tips

    You can run the whole docker compose stack with this simple command:

    ```console
    docker compose --profile "*" up -d
    ```

## Running the database

Running the database can be simply done via the following command:

```console
docker compose --profile database up -d
```

Example of docker compose stac file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:
  database:
    image: postgres:16
    profiles:
      - database
    restart: unless-stopped
    ports:
      - 5432:5432
    environment:
      - POSTGRES_PASSWORD=changeme
      - POSTGRES_USER=resonitecommunities
      - POSTGRES_DB=resonitecommunities
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U resonitecommunities"]
      interval: 1m30s
      timeout: 30s
      retries: 5
      start_period: 30s

volumes:
  postgres_data:
    driver: local
```

### Migrations

The service for the migration in the docker compose file is run directly by the the manager service and clients.

Example of docker compose stack file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:

  # Here goes the database docker compose service definition

  migrations:
    build: backend
    command: poetry run alembic upgrade head
    depends_on:
      database:
        condition: service_healthy
    profiles:
      - manager
      - clients

  # Here goes the volume information for the database

```

## Running the manager

!!! warning

    This require the database to be running.

Running the manager can be simply done via the following command:

```console
docker compose --profile manager --profile database up -d
```

Example of docker compose stac file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:

  # Here goes the database docker compose service definition

  # Here goes the manager docker compose service definition

  signals_manager:
    build: backend
    restart: always
    command: poetry run signals_manager
    profiles:
      - manager
    depends_on:
      migrations:
        condition: service_completed_successfully
      database:
        condition: service_healthy
    volumes:
      - "./backend/config.toml:/app/config.toml"

  # Here goes the volume information for the database
```

!!! tip

    If you want to the manager container you also need to stop the database one too:

    ```console
    docker compose --profile client --profile database down
    ```

    And to restart it use the `up` command.

## Running the clients

!!! warning

    This require the database to be running.

    It's also a good idea to have the manager running to fill the database with signals.

Running the manager can be simply done via the following command:

```console
docker compose --profile clients --profile database up -d
```

Example of docker compose stac file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:

  # Here goes the database docker compose service definition

  # Here goes the manager docker compose service definition

  api_client:
    build: backend
    restart: always
    profiles:
      - client
    command: poetry run api_client
    depends_on:
      migrations:
        condition: service_completed_successfully
      database:
        condition: service_healthy
    volumes:
      - "./backend/config.toml:/app/config.toml"
    ports:
      - '8000:8000'
  web_client:
    build: backend
    restart: always
    profiles:
      - client
    command: poetry run web_client
    depends_on:
      migrations:
        condition: service_completed_successfully
      database:
        condition: service_healthy
    volumes:
      - "./backend/config.toml:/app/config.toml"
    ports:
      - '8001:8001'

  # Here goes the volume information for the database
```

!!! tip

    If you want to the clients containers you also need to stop the database one too:

    ```console
    docker compose --profile client --profile database down
    ```

    And to restart it use the `up` command.

## Running the proxy

We use traefik to handle this notion of new and old url.

```yaml
  traefik:
    image: traefik:v3.3
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entryPoints.web.address=:80"
      - "--accesslog=true"
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"

  # Here goes the database docker compose service definition

  # Here goes the manager docker compose service definition

  # Here goes the api client docker compose service definition

  # Labels for the api client docker compose service definition
      labels:
      - traefik.enable=true

      # Modern API route
      - traefik.http.routers.api_client.rule=Host(`resonite-communities.local`) && PathPrefix(`/api`)
      - traefik.http.routers.api_client.entrypoints=web

      # Private events legacy API route
      - traefik.http.routers.api_client_legacy_private.rule=Host(`private.resonite-communities.local`) && PathPrefix(`/v1`)
      - traefik.http.routers.api_client_legacy_private.entrypoints=web

      # Public events legacy API route
      - traefik.http.routers.api_client_legacy_public.rule=Host(`resonite-communities.local`) && PathPrefix(`/v1`)
      - traefik.http.routers.api_client_legacy_public.entrypoints=web

  # Here goes the web client docker compose service definition

  # Labels for the web client docker compose service definition
    labels:
      - traefik.enable=true
      - traefik.http.routers.web_client.rule=Host(`resonite-communities.local`)
      - traefik.http.routers.web_client.entrypoints=web

  # Here goes the volume information for the database
```