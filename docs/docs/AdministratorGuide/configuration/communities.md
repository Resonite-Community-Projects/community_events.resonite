---
title: Communities
prev: AdministratorGuide/configuration/application.md
next: AdministratorGuide/configuration/users.md
---

In the web interface, administrators and moderators manage communities. (See the [Users](users.md) section)

!!! note

    Internally these are called `signals`, but throughout this guide we use the term `community`.

A community represents a group of events or streams that an instance can follow.

There are two main types:

- **Event communities**: provide events from external platforms.
- **Stream communities**: provide streams from external platforms.

Communities come from different sources.

Supported sources for event communities are:

- **Discord**
- **JSON**
- **JSON Community Event**


Supported sources for stream communities are:

- **Twitch**

## Adding a community

Communities can only be added manually, but some sources allow automatic detection of available communities.

### Event communities

#### Discord

Discord communities connected through the bot are automatically detected.

To add one connected through the bot:

1. Click **Add event community auto** to select a detected Discord community.
2. By default, new communities are created with the tag `private` to avoid leaking private events.
3. To make it public immediately, switch the tag to `public` before saving.

!!! note

    The `public` or `private` status is only a tag. It can be changed later when editing the community.

To add manually:

1. Create a new community of type **Discord**.
2. Save the community.

#### JSON

A JSON-based community must be added manually.

1. Create a new community of type **JSON**.
2. Enter the server URL that provides the JSON file.
3. Save the community.

#### JSON Community Event

A JSON Community Event is a remote instance of the Resonite community event system.

1. First, add a new community with the platform **JSON Community Event** (do not set the source URL here).
2. Save the community.
3. Edit the community and add the root URL in the **Server URL** field with `https://` in front.
4. Save again.
5. Edit the community one more time to see the list of available remote communities.

!!! note

    Only `public` remote communities are listed.
    If a community already exists locally, it will still appear in the list but cannot be added.

### Streams communities

#### Twitch

## Edit community

These keys are available for all communities:

| Key | Type | Description |
| :--- | :--- | :--- |
| `Name` | `str` | The name of the community |
| `Platform ID` | `str` | The external ID of the community, the Discord snowflake of the community for example |
| `Description` | `str` | The description of the community |
| `URL` | `str` | The URL where to find the community, can be a Discord invite, a link to website, etc. |
| `Tags` | `list[str]` | Tags to classify the community, e.g. `public` or `private`. See [[Difference between public and private community]] for more information |

### Event communities

Event communities have additional configuration keys.

#### Discord

| Key | Type | Description |
| :--- | :--- | :--- |
| `Private Role ID` | `int` | For a private community, the Discord user role that grant access to the private events. |
| `Private Channel ID` | `int` | For a private community, the Discord audio channel ID used to define when an event is private (Because of Discord restrictions). |

#### JSON

| Key | Type | Description |
| :--- | :--- | :--- |
| `Server URL` | `str` | The server URL to get the JSON file from. |

#### JSON Community Event

| Key | Type | Description |
| :--- | :--- | :--- |
| `Server URL` | `str` | The server URL to get the remote community events from. |
| `Remote communities` | `list` | List of community that can be followed. |

### Stream communities

#### Twitch

Stream communities do not have additional configuration keys.