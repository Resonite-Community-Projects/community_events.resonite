---
title: Infrastructure
prev: AdministratorGuide/configuration/configuration.md
next: AdministratorGuide/configuration/database.md
---

## Infrastructure configuration

Use for infrastructure-level settings that are unlikely to change, such as database credentials and secret keys.

| Variable | Type | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `str` | A secret key used to handle the authentication system |
| `SECRET` | `str` | The secret key use to handle the authentication system |
| `PUBLIC_DOMAIN` | `str` | The domain used by the HTTP API do show only the public events |
| `PRIVATE_DOMAIN` | `str` | The domain used by the HTTP API to show only the private events |
| `DATABASE_URL` | `str` | The Postgresql database url |
| `CACHE_URL` | `str` | The Redis database url |
| `SENTRY_DSN` | `str` | The DSN configuration for send error logs to Sentry |

### Setting up `PUBLIC_DOMAIN` and `PRIVATE_DOMAINT`

To be able to use the HTTP API locally you need to configure your hosts file on your file system with the following domain:

Depending on your Operating System this would either by `/etc/hosts` for linux or `C:\Windows\System32\drivers\etc\hosts` for Windows. Be careful that modifing this file require you to be administrator of you computer.

```hosts title="hosts"
127.0.0.1 resonite-communities.local
127.0.0.1 private.resonite-communities.local
```

You can change the second-level domain but there is a check on the top-level domain `.local` in the code, even if this is just to show an tip message.

This check is done in the function `check_is_local_env` in the class utils and is used with the variable `is_local_env` in the rest of the code.

### Setting up `DATABASE_URL`

In the case you want to do local developement switching between the docker containers and without for the manager and the clients you will need to configure the following for running the `poetry run` command directly:

```toml
DATABASE_URL = "postgresql://resonitecommunities:changeme@127.0.0.1:5432/resonitecommunities"
```

Or this configuration if you want to use the `poetry run` command via the docker compose:

```toml
DATABASE_URL = "postgresql://resonitecommunities:changeme@database:5432/resonitecommunities"
```

### Setting up `CACHE_URL`

In the case you want to do local developement switching between the docker containers and without for the signal manager you will need to configure the following for running the `poetry run` command directly:

```toml
CACHE_URL = "redis://127.0.0.1"
```

Or this configuration if you want to use the `poetry run` command via the docker compose:

```toml
CACHE_URL = "redis://cache"
```

### Discord

| Variable | Type | Description |
| :--- | :--- | :--- |
| `DISCORD_CLIENT_ID` | `int` | the id of the Discord client |
| `DISCORD_SECRET` | `str` | the secret of the Discord client |
| `DISCORD_REDIRECT_URL` | `str` | the callback url for Discord API to call when finishing the authentification process on their end. |

#### Discord bot configuration

When creating the bot on Discord Application interface you need to set some parameters to work.

##### Installation section

Installation context set to **only** `Guild Install`

Set the scope to `bot`, we don't need the `applications_commands`

##### Bot section

Enable the following intents:

- `Presence`
- `Server Members`
- `Message Content`

