# Server Installation

!!! info

    During the development you only need tu run the database but while we explain everything here, a fully working docker compose example file is available at the root of the project.

    You **don't need** to create your own based on this instruction as this is an explanation from the already exist docker compose file. But use the command as needed.

We use docker compose `profiles` to separate each componants in groups: `database`, `manager` and `clients`.

!!! tips

    You can run the whole docker compose stack with this simple command:

    ```console
    docker compose --profile "*" up
    ```

## Running the database

Running the database can be simply done via the following command:

```console
docker compose --profile database up
```

Example of configuration file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
```

## Running the manager

!!! warning

    This require the database to be running.

Running the manager can be simply done via the following command:

```console
docker compose --profile manager up
```

Example of configuration file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:

  # Here goes the database docker compose configuration

  .. TODO: Put the configuration here

  # Here goes the volume information for the database
```

## Running the clients

!!! warning

    This require the database to be running.

    It's also a good idea to have the manager running to fill the database with signals.

Running the manager can be simply done via the following command:

```console
docker compose --profile clients up
```

Example of configuration file (fully working but extract still from the docker compose example file at the root of the project):

```yaml
services:

  # Here goes the database docker compose configuration

  # Here goes the manager docker compose configuration

  .. TODO: Put the configuration here

  # Here goes the volume information for the database
```