---
title: Migrations
prev: DeveloperGuide/development/usage.md
next: DeveloperGuide/development/testing.md
---

For handling the migrations of the database we use Alembic.

## Create a new migration

After running this command, a new migration script will be created in the `migrations/versions` directory. It is crucial to review this script to ensure that it accurately reflects the intended changes. Alembic is not always perfect and may require manual adjustments.

```console
poetry run alembic revision --autogenerate -m "Migration name"
```

## Apply a migration

```console
poetry run alembic upgrade head
```

## Testing a migration

When testing a migration you should play around with the upgrade and downgrade commands.

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
