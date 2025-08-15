---
title: Database
prev: AdministratorGuide/configuration/infrastructure.md
---

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