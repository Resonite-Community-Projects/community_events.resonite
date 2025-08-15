---
title: Configuration
prev: DeveloperGuide/deployment/installation.md
---


The configuration is splited in different parts. A general configuration as well as per collectors and transmittors for events.

Anything related to the infrastructure have to be set using environment variable otherwise the configuration would be in the database
accessible via the web interface `/admin/configuration`.

!!! warning

    When the configuration is changed you **must** restart all the services.

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

## Database configuration

Use for application-level settings that you might want to change without restarting the server, such as community settings and refresh intervals. These can be managed through the admin interface.

### Resonite

| Key | Type | Description |
| :--- | :--- | :--- |
| `Facet URL` | `str` | he Resonite public folder url where the facet is store |

### Discord

| Key | Type | Description |
| :--- | :--- | :--- |
| `Discord Bot Token` | `str` | The Discord bot for public event |
| `Ad Discord Bot Token` | str` | The Discord bot for private event (See why it's deprecated) |


### Twitch

| Key | Type | Description |
| :--- | :--- | :--- |
| `Client ID` | `str` | The client id for Twitch |
| `Secret` | `str` | The secret for Twitch |
| `Game ID` | `str` | The Resonite Twitch game id to follow |
| `Account Name` | `str` | The Resonite Twitch account name to follow |

## Collectors

| Key | Type | Description |
| :--- | :--- | :--- |
| `Refresh Interval` | `int` | The number of minute between each refresh interval of the signals |

## Signals configuration

A collector is a signal who will retrieve informations from different source. Not all keys are mandatory for a collector.

They have a dedicated page in the admin web interface to be configured `/admin/communities`. They are splitted in two different kind
of communities: Event and Streams.


#### General settings available

| Key | Type | Description |
| :--- | :--- | :--- |
| `Name` | `str` | the name of this signal |
| `Platform ID` | `str` | the external id of this signal, the Discord snowflake of the community for example |
| `Description` | `str` | the description of this signall |
| `URL` | `str` | the URL where to find the community, can be a discord invite, a link to website, etc |
| `Tags` | `list[str]` | the list of tags related to the community, use to differenciate if a community is public or private. See [[Difference between public and private community]] for more information |

#### Event communities

| Key | Type | Description |
| :--- | :--- | :--- |
| `Platform` | `str` | either JSON or Discord. Based on the choice different configuration keys are available. |

##### Configuration keys

###### General

| Key | Type | Description |
| :--- | :--- | :--- |
| `Private Role ID` | `int` | For a private community, the Discord user role who define that they have access to the private events |
| `Private Channel ID` | `int` | For a private community, the Discord audio channel id used to define when an event is private (Because of Discord restrictions) |

###### JSON

| Key | Type | Description |
| :--- | :--- | :--- |
| `Server URL` | `str` | the server URL |

#### Streams communities

Nothing special.


## Templating

It's possible to configure a bit the theme. There is different keys available in the database for that.

| Key | Type | Description |
| :--- | :--- | :--- |
| `Hero color` | `str` | CSS formatted value for `background` |
| `Title Text` | `str` | Title of the service  |
| `Info Text` | `html` | HTML formatted code |
| `Footer Text` | `html` | HTML formatted code |

If you ever want to update the logo and you happen to use docker, simply mount the new
logo in a volume and override the existing one at `resonite_communities/clients/web/static/images/icon.png`.