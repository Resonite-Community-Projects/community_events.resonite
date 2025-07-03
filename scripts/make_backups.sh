#!/bin/bash
echo "Stop signals manager"

docker compose --profile "*" stop signals_manager

echo "Backup communities..."
docker compose run --rm --env PGPASSWORD='changeme' -v "./backups:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t community --data-only -F p -f /backups/community.sql

echo "Backup streams..."
docker compose run --rm --env PGPASSWORD='changeme' -v "./backups:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t stream --data-only -F p -f /backups/stream.sql

echo "Backup events..."
docker compose run --rm --env PGPASSWORD='changeme' -v "./backups:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t event --data-only -F p -f /backups/event.sql

echo "Start signals manager"
docker compose --profile "*" start signals_manager