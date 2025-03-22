# Architecture

!!! construction "This need to be documented"

Explain here about the architecture with the signals stuff. Like collectors and transmistors.

## Modularity note

The `bots` folder contains a list of modules to get events from. While
most of them are and will be for discord bot there is actually two
exception, for now. The module called `google` and `discord` are
for Google Calendar and Discord integrated event system. All of the
bot are based on the class `Bot` in the `_base.py` file.

## Utils

For found what is the id of a guild you can use the script `get_discord_server_list.py` who return the list of guild where the bot is
present.