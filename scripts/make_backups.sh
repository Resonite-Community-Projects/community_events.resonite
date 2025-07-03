#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +"%F_%H%M") # YYYY-MM-DD_HHMM
STACK_NAME=""

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Backup PostgreSQL tables using Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name
  --date DATE_TIME      (optional) Override timestamp (format: YYYY-MM-DD_HHMM)
  --help                Show this help message and exit

Examples:
  $0                             Run backup in current folder (default stack)
  $0 --stack my_stack            Run backup for a named stack
  $0 --date 2025-07-03_1430      Backup using a fixed datetime
EOF
}

# Parse args
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --stack)
            STACK_NAME="$2"
            shift 2
            ;;
        --date)
            DATE="$2"
            shift 2
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo
            print_help
            exit 1
            ;;
    esac
done

# Compose command with optional stack
COMPOSE="docker compose"
[[ -n "$STACK_NAME" ]] && COMPOSE+=" -p $STACK_NAME"

echo "Using Docker Compose stack: ${STACK_NAME:-default from folder}"
echo "Backup datetime: $DATE"
echo

echo "Stop signals manager"
$COMPOSE --profile "*" stop signals_manager

echo "Backup communities..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t community \
  --data-only -F p -f "/backups/community_${DATE}.sql"

echo "Backup streams..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t stream \
  --data-only -F p -f "/backups/stream_${DATE}.sql"

echo "Backup events..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t event \
  --data-only -F p -f "/backups/event_${DATE}.sql"

echo "Start signals manager"
$COMPOSE --profile "*" start signals_manager
