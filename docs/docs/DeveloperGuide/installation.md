# Installation

The base requirement for this project is to have [Python](https://www.python.org/) `3.12.*` as well as [Poetry](https://python-poetry.org/).

Since the installation process of this requirement can be really different from one Operating System to another we will not cover them here. Please refer to the documentation available for your Operating System.

While there is a Dockerfile as well as a docker-compose file available in the project this are not useful for the development, please see directly [the dedicated section for more information](server-installation.md).

While we still need a database for the developement [SQLite](https://www.sqlite.org/) is used and so removing the requirement to start a full instance of [Postgresql](https://www.postgresql.org/). (You have nothing to do here)

We also take advantage of using [VSCode](https://code.visualstudio.com/) and [devcontainer](https://containers.dev/). (See the [VSCode documentation for the requirements to use devcontainer in VSCode](https://code.visualstudio.com/docs/devcontainers/containers))

## VSCode setup and Devcontainer

!!! note

    Keep in mind you don't need neither VSCode or devcontainer to help during the development but this will help you to get started easly, if you have the tools (like Docker) already configured.

If you already follow the [VSCode documentation for the requirements to use devcontainer in VSCode](https://code.visualstudio.com/docs/devcontainers/containers) you should be able to ask VSCode to restart the project that you have recently cloned via the command `Dev Container: Rebuild Container`.

If this is the first time you use devcontainer it will take sometime this is normal.

To check the configuration of the devcontainer you can directly check the [.devcontainer/devcontainer.json](https://github.com/Resonite-Community-Projects/community_events.resonite/blob/master/.devcontainer/devcontainer.json) file.

## Project installation

No matter if you are in a devcontainer or no you can use Poetry to start install your project in a Python virtual environment:

```console
poetry install
```

!!! danger

    You must be in the folder `backed` to run this command.