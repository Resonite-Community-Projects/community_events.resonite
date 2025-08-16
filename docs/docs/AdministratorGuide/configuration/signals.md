---
title: Signals
prev: AdministratorGuide/configuration/database.md
next: AdministratorGuide/configuration/users.md
---

A signal (commonly called a community) is configurable from the Web Interface`/admin/communities`. You must have either the role `administrator` or `moderator` (See the [Users](users.md) section).

They are regrouped in two different kind: Event and Streams.

!!! Danger

    Some of the keys required to have the server to be restarted to be taken into account for now. Each field will have this information directly on the configuration page.

## Add community

You can either manually add a community.

For events communities, as they come directly from Discord, they are automaticly detect and pre configured. To see them you have the button `Add event community auto` that will show you a list of them.

By default, to avoid any mistake they are set to `private` to avoid any leak of private events. If you switch **before** adding it to `public` then the community will be public.

Keep in mind this just adding a `tag` to the community `public` or `private` so in case of a mistake you can simply change the `tag` here.

## Edit community

### General settings available

Keys that are available no matter the kind of signal.

| Key | Type | Description |
| :--- | :--- | :--- |
| `Name` | `str` | The name of this signal |
| `Platform ID` | `str` | The external id of this signal, the Discord snowflake of the community for example |
| `Description` | `str` | The description of this signall |
| `URL` | `str` | The URL where to find the community, can be a discord invite, a link to website, etc |
| `Tags` | `list[str]` | The list of tags related to the community, use to differenciate if a community is public or private. See [[Difference between public and private community]] for more information |

### Event communities

| Key | Type | Description |
| :--- | :--- | :--- |
| `Platform` | `str` | Either JSON or Discord. Based on the choice different configuration keys are available. |

#### Configuration keys

##### General

| Key | Type | Description |
| :--- | :--- | :--- |
| `Private Role ID` | `int` | For a private community, the Discord user role who define that they have access to the private events. |
| `Private Channel ID` | `int` | For a private community, the Discord audio channel id used to define when an event is private (Because of Discord restrictions). |

##### JSON

| Key | Type | Description |
| :--- | :--- | :--- |
| `Server URL` | `str` | The server URL to get the JSON file from. |

### Streams communities

Nothing.
