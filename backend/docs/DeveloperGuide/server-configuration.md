# Server Configuration

The configuration is splited in different parts. A general configuration as well as per collectors and transmittors for events.

!!! warning

    When the configuration is changed you **must** restart all the services.

Most of the configuration of this tool are available in the `config.toml` file.

## General

- `SECRET_KEY`: str, The secret key use to handle the authentication system
- `REFRESH_INTERVAL`: int, The number of minute between each refresh interval of the signals
- `SECRET`: str, The secret key use to handle the authentication system
- `PUBLIC_DOMAIN`: str, The domain used by the HTTP API do show only the public events
- `PRIVATE_DOMAIN`: str, The domain used by the HTTP API to show only the private events

!!! note "About the domains"

    To be able to use the HTTP API locally you need to configure your hosts file on your file system with the following domain:

    Depending on your Operating System this would either by `/etc/hosts` for linux or `C:\Windows\System32\drivers\etc\hosts` for Windows. Be careful that modifing this file require you to be administrator of you computer.

    ```hosts title="hosts"
    127.0.0.1 resonite-communities.local
    127.0.0.1 private.resonite-communities.local
    ```

    You can change the second-level domain but there is a check on the top-level domain `.local` in the code, even if this is just to show an tip message.

## Resonite

- `FACET_URL`: str, The Resonite public folder url where the facet is store

## Discord

- `DISCORD_BOT_TOKEN`: str, The Discord bot for public event
- `AD_DISCORD_BOT_TOKEN`: str, The Discord bot for private event (See why it's deprecated)
- `Discord.client_bot_token`: str, The Discord bot token
- `Discord.client.id`: int, the id of the Discord client
- `Discord.client.secret` str, the secret of the Discord client
- `Discord.client.redirect_uri`: str, the callback url for Discord API to call when finishing the authentification process on their end.

## Twitch

- `Twitch.client_id`: str, The client id for Twitch
- `Twitch.secret`: str, The secret for Twitch
- `Twitch.game_id`: str, The Resonite Twitch game id to follow
- `Twitch.account_name`: str, The Resonite Twitch account name to follow

## Collectors

A collector is a signal who will retrieve informations from different source. Not all keys are mandatory for a collector.

### Configuration keys availables

- `external_id`: str, the external id of this signal, the Discord snowflake of the community for example
- `name`: str, the name of this signal
- `description`: str, the description of this signal
- `url`: str, the URL where to find the community, can be a discord invite, a link to website, etc
- `tags`: list of str, the list of tags related to the community, use to differenciate if a community is public or private. See [[Difference between public and private community]] for more information
- `config`: object, the special configuration for this community

### DiscordEventsCollector

The source module for discord integrated schedule events system.

!!! info "Mendatory keys"

    `external_id`, `name`

#### Custom configuration

- `private_role_id`: int, For a private community, the Discord user role who define that they have access to the private events
- `private_channel_id`: int, For a private community, the Discord audio channel id used to define when an event is private (Because of Discord restrictions)

#### Examples

!!! example "Public community example"

    ```
    [[SIGNALS.DiscordEventsCollector]]
    external_id = xxxxxxxxxxxxxxxxxx
    name = "The Vulpine Garden"
    description = "The Vulpine Garden Community"
    url = "https://discord.gg/xxxxxxxx"
    tags = ['public', 'karaoke']
    ```

!!! example "Private community example"

    ```
    [[SIGNALS.DiscordEventsCollector]]
    external_id = xxxxxxxxxxxxxxxxxx
    external_id = "The Vulpine Garden"
    name = "The Vulpine Garden Community"
    description = "https://discord.gg/xxxxxxxx"
    tags = ['private', 'karaoke']
    config.private_role_id = xxxxxxxxxxxxxxxxxxx
    config.private_channel_id = xxxxxxxxxxxxxxxxxxx
    ```


### TwitchStreamsCollector

The source module for Twitch streams.

!!! info "Mendatory keys"

    `external_id`, `name`

#### Examples

!!! example

    ```
    [[SIGNALS.TwitchStreamsCollector]]
    external_id = "resoniteapp"
    name = "resoniteapp"
    ```

## Transmittors

Not yet available.