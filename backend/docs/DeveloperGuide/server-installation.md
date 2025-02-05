# Server Installation

!!! todo

    This is the old docker-compose file, this need to be redone

For having your own local instance of the system you can use the following docker-compose file:

```yaml
services:
  cache:
    image: redis:7.0-alpine
    restart: always
    command: redis-server --save 20 1 --loglevel warning
  bots:
    build: backend
    restart: always
    command: poetry run signals_manager
    depends_on:
      - "cache"
    volumes:
      - "./config.toml:/app/config.toml"
      - "./credentials.json:/app/credentials.json"
  web:
    build: backend
    restart: always
    command: poetry run web_client
    depends_on:
      - "cache"
    volumes:
      - "./config.toml:/app/config.toml"
      - "./credentials.json:/app/credentials.json"
    ports:
      - '5000:8000'
  worker:
    build: .
    restart: always
    command: celery -A resonite_communities.tasks worker -l info
    depends_on:
      - "cache"
    volumes:
      - "./config.toml:/app/config.toml"

```