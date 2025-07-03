#!/bin/bash
echo "Stop signals manager"

docker compose --profile "*" stop signals_manager

echo "Clean streams..."
docker compose run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -c "TRUNCATE TABLE stream;"

echo "Clean events..."
docker compose run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -c "TRUNCATE TABLE event;"

echo "Clean communities..."
docker compose run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -c "TRUNCATE TABLE stream, event, community;"


echo "Start signals manager"
docker compose --profile "*" start signals_manager