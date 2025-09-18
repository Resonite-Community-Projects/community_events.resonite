---
title: Environment
prev: AdministratorGuide/configuration/configuration.md
next: AdministratorGuide/configuration/application.md
---

Use for infrastructure-level settings that are unlikely to change, such as database credentials and secret keys.

## Required Variables

These variables must be set for the application to function properly.

| Variable | Type | Description |
| :--- | :--- | :--- |
| `PUBLIC_DOMAIN` | `str` | The domain used by the HTTP API to show only the public events |
| `DATABASE_URL` | `str` | The PostgreSQL database URL |
| `CACHE_URL` | `str` | The Redis database URL |
| `SECRET_KEY` | `str` | A secret key used to handle the authentication system |
| `SECRET` | `str` | The secret key used to handle the authentication system |
| `DISCORD_CLIENT_ID` | `int` | The ID of the Discord client |
| `DISCORD_SECRET` | `str` | The secret of the Discord client |
| `DISCORD_REDIRECT_URL` | `str` | The callback URL for Discord API authentication |
| `SENTRY_DSN` | `str` | The DSN configuration for sending error logs to Sentry |

## Optional Variables

Some of these variables have default values and can be customized as needed.

### Domain Configuration

| Variable | Type | Description |
| :--- | :--- | :--- |
| `PRIVATE_DOMAIN` | `str` | The domain used by the HTTP API to show only the private events |

### Database Connection Pool

| Variable | Type | Description |
| :--- | :--- | :--- |
| `DB_POOL_SIZE` | `int` | Database connection pool size (default: 6) |
| `DB_MAX_OVERFLOW` | `int` | Maximum overflow connections for database pool (default: 8) |
| `DB_POOL_TIMEOUT` | `int` | Database connection timeout in seconds (default: 30) |
| `DB_POOL_RECYCLE` | `int` | Database connection recycle time in seconds (default: 1800) |
| `DB_POOL_PRE_PING` | `bool` | Whether to pre-ping database connections (default: true) |

### Application Workers

| Variable | Type | Description |
| :--- | :--- | :--- |
| `WEB_WORKERS` | `int` | Number of web application workers (default: 3) |
| `API_WORKERS` | `int` | Number of API application workers (default: 3) |

!!! note

    Keep in mind that the signal manager is counted as 1 worker and is not configurable yet.

## Configuration Guides

### Domain Setup

To use the HTTP API locally, configure your hosts file with the following domains:

- **Linux/Mac:** `/etc/hosts`
- **Windows:** `C:\Windows\System32\drivers\etc\hosts`

```hosts title="hosts"
127.0.0.1 resonite-communities.local
127.0.0.1 private.resonite-communities.local
```

!!! note
    The code checks for the `.local` top-level domain to detect local environments.

### Database Configuration

**For direct Poetry runs:**
```toml
DATABASE_URL = "postgresql://resonitecommunities:changeme@127.0.0.1:5432/resonitecommunities"
```

**For Docker Compose runs:**
```toml
DATABASE_URL = "postgresql://resonitecommunities:changeme@database:5432/resonitecommunities"
```

### Performance Tuning

The default values for database connection pool and application workers are based on tests on the community instance.

They are based on the default settings of PostgreSQL which have a limit of 100 connections.

### Discord Bot Setup

When creating the Discord bot application, configure these settings:

**Installation Section:**

- Installation context: Guild Install only
- Scope: bot (`applications_commands` not needed)

**Bot Section - Required Intents:**

- Presence
- Server Members
- Message Content
