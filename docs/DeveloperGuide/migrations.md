# Migrations

For handling the migrations of the database we use Alembic.

## Create a new migration

```console
poetry run alembic revision --autogenerate -m "Migration name"
```

## Apply a migration

```console
poetry run alembic upgrade head
```

## Handling migration issues

To look through the migration history, one can simply look into the history

```console
poetry run alembic history
```

And then upgrade or downgrade as needed. Examples commands:

```console
poetry run alembic upgrade head # To go the last version
poetry run alembic upgrade <migration hash> # To upgrade to a certain version
poetry run alembic downgrade <migration hash> # To downgrade to a certain version
```