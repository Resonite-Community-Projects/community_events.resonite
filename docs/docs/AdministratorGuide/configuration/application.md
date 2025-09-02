---
title: Application
prev: AdministratorGuide/configuration/environment.md
next: AdministratorGuide/configuration/communities.md
---

Use for application-level settings that you might want to change without restarting the server, such as community settings and refresh intervals. These can be managed through the admin interface.

!!! Danger

    Some of the keys required to have the server to be restarted to be taken into account for now. Each field will have this information directly on the configuration page.

## Resonite

| Key | Type | Description |
| :--- | :--- | :--- |
| `Facet URL` | `str` | he Resonite public folder url where the facet is store |

## Discord

| Key | Type | Description |
| :--- | :--- | :--- |
| `Discord Bot Token` | `str` | The Discord bot for public event |
| `Ad Discord Bot Token` | str` | The Discord bot for private event (See why it's deprecated) |


## Twitch

| Key | Type | Description |
| :--- | :--- | :--- |
| `Client ID` | `str` | The client id for Twitch |
| `Secret` | `str` | The secret for Twitch |
| `Game ID` | `str` | The Resonite Twitch game id to follow |
| `Account Name` | `str` | The Resonite Twitch account name to follow |

## Signal refresh interval

Collectors and Transmitter have a refresh interval before they will be triggered again.

| Key | Type | Description |
| :--- | :--- | :--- |
| `Refresh Interval` | `int` | The number of minute between each refresh interval of the signals |

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
