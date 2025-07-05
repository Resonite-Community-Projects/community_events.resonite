#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +"%F_%H%M") # YYYY-MM-DD_HHMM
STACK_NAME=""
CONFIG_FILE="./stack-aliases.conf"

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Backup PostgreSQL tables using Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name or alias
  --date DATE_TIME      (optional) Override timestamp (format: YYYY-MM-DD_HHMM)
  --config FILE         (optional) Set custom config file path (default: ./stack-aliases.conf)
  --help                Show this help message and exit

Examples:
  $0                             Run backup in current folder (default stack)
  $0 --stack prod                Use alias from config file
  $0 --stack my_stack            Use explicit stack name
  $0 --config ./my_aliases.conf  Use custom config file
EOF
}

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
        --config)
            CONFIG_FILE="$2"
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

if [[ -n "$STACK_NAME" && -f "$CONFIG_FILE" ]]; then
    ALIAS_VALUE=$(grep "^$STACK_NAME=" "$CONFIG_FILE" | cut -d'=' -f2-)
    if [[ -n "$ALIAS_VALUE" ]]; then
        echo "Resolved stack alias '$STACK_NAME' to '$ALIAS_VALUE'"
        STACK_NAME="$ALIAS_VALUE"
    fi
fi

COMPOSE="docker compose"
[[ -n "$STACK_NAME" ]] && COMPOSE+=" -p $STACK_NAME"

echo "Using Docker Compose stack: ${STACK_NAME:-default from folder}"
echo "Backup datetime: $DATE"
echo

echo "Stop signals manager"
$COMPOSE --profile "*" stop signals_manager

STACK_PREFIX="${STACK_NAME:+${STACK_NAME}_}"

echo "Backup communities..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t community \
  --data-only -F p -f "/backups/community_${STACK_PREFIX}${DATE}.sql"

echo "Backup streams..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t stream \
  --data-only -F p -f "/backups/stream_${STACK_PREFIX}${DATE}.sql"

echo "Backup events..."
$COMPOSE run --rm --env PGPASSWORD='changeme' -v "$BACKUP_DIR:/backups" database pg_dump \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities -t event \
  --data-only -F p -f "/backups/event_${STACK_PREFIX}${DATE}.sql"

echo "Start signals manager"
$COMPOSE --profile "*" start signals_manager
