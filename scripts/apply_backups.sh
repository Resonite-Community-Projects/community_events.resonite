#!/bin/bash
set -e

echo "Stop signals manager"
docker compose --profile "*" stop signals_manager

echo "Restore communities..."
docker compose run --rm --env PGPASSWORD='changeme' -v "$(pwd)/backups:/backups" database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities --set ON_ERROR_STOP=off -f /backups/community.sql

echo "Restore streams..."
docker compose run --rm --env PGPASSWORD='changeme' -v "$(pwd)/backups:/backups" database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities --set ON_ERROR_STOP=off -f /backups/stream.sql

echo "Restore events..."
docker compose run --rm --env PGPASSWORD='changeme' -v "$(pwd)/backups:/backups" database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities --set ON_ERROR_STOP=off -f /backups/event.sql

echo "Start signals manager"
docker compose --profile "*" start signals_manager
