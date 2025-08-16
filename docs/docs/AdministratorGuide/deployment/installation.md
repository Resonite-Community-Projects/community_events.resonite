---
title: Installation
prev: AdministratorGuide/deployment/requirements.md
next: AdministratorGuide/configuration/configuration.md
---


!!! Info

    This is a simple explanation of our current stack is configured for you to do the same if you ever want to run your own server for your own community.

!!! info

    During the development you only need tu run the database but while we explain everything here, a fully working docker compose example file is available at the root of the project.

    You **don't need** to create your own based on this instruction as this is an explanation from the already exist docker compose file. But use the command as needed.

We use docker compose `profiles` to separate each components in groups: `database`, `manager` and `clients`.

!!! tips

    You can run the whole docker compose stack with this simple command:

    ```console
    docker compose --profile "*" up -d
    ```

## Running the proxy

We use traefik to handle the routing in our stack. The label are indicated here directly instead of per stack.

Running the proxy can be simply done via the following command:

```console
docker compose --profile "router" up -d
```

Stack example:

```yaml
  traefik:
    image: traefik:v3.3
    profiles:
      - router
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

## Running the database

Running the database can be simply done via the following command:

```console
docker compose --profile "database" up -d
```

Stack example:

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

!!! warning

    This service is run through the `manager` and `clients` services.

Stack example:

```yaml
services:

  # Here goes the database docker compose service definition

  migrations:
    build: backend
    command: >
      /bin/bash -c "
      poetry run alembic upgrade head;
      EXIT_CODE=$?;
      if [ $EXIT_CODE -ne 0 ]; then
        echo 'Alembic migration failed with exit code' $EXIT_CODE;
        exit $EXIT_CODE;
      fi
      "
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

    This service require the `database` and the `proxy` services.

Running the manager can be simply done via the following command:

```console
docker compose --profile "database" --profile "proxy" --profile "manager" up -d
```

!!! note

    When you need to put down the signals manager you also need to precise the profiles the same way your run it.

    ```console
    docker compose --profile "database" --profile "proxy" --profile "manager" down
    ```

Stack example:

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

## Running the clients

!!! warning

    This service require the `database` and the `proxy` services.

!!! tip

    It's a good idea to have the signals manager running to fill the database with events and streams.

Running the signals manager can be simply done via the following command:

```console
docker compose --profile "database" --profile "proxy" --profile "clients"  up -d
```

!!! note

    When you need to put down the clients you also need to precise the profiles the same way your run it.

    ```console
    docker compose --profile "database" --profile "proxy" --profile "clients" down
    ```

Stack example:

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
