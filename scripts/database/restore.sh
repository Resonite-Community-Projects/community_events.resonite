#!/bin/bash
set -e

BACKUP_DIR="./backups"
TARGET_DATE=""
STACK_NAME=""

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Restore PostgreSQL backups using Docker Compose.

Options:
  --date TIMESTAMP       Restore from specific backup timestamp (e.g. 2025-07-03_1645)
  --date latest          Restore from the latest available backup
  --stack STACK_NAME     (optional) Specify Docker Compose project name
  --list                 List all available backup timestamps
  --help                 Show this help message and exit

Examples:
  $0 --date latest
  $0 --stack my_stack --date 2025-07-03_1645
  $0 --list
EOF
}

if [[ $# -eq 0 ]]; then
    print_help
    exit 0
fi

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --date)
            TARGET_DATE="$2"
            shift 2
            ;;
        --stack)
            STACK_NAME="$2"
            shift 2
            ;;
        --list)
            echo "Available backup timestamps:"
            find "$BACKUP_DIR" -type f -name '*.sql' \
                | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}' \
                | sort -u
            exit 0
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

COMPOSE="docker compose"
[[ -n "$STACK_NAME" ]] && COMPOSE+=" -p $STACK_NAME"

if [[ "$TARGET_DATE" == "latest" || -z "$TARGET_DATE" ]]; then
    TARGET_DATE=$(find "$BACKUP_DIR" -type f -name '*.sql' \
        | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}' \
        | sort -u | tail -n 1)
    if [[ -z "$TARGET_DATE" ]]; then
        echo "No backup files found in $BACKUP_DIR"
        exit 1
    fi
    echo "Using latest backup: $TARGET_DATE"
fi

COMMUNITY_FILE="$BACKUP_DIR/community_${TARGET_DATE}.sql"
STREAM_FILE="$BACKUP_DIR/stream_${TARGET_DATE}.sql"
EVENT_FILE="$BACKUP_DIR/event_${TARGET_DATE}.sql"

echo
echo "The following backup files will be restored (stack: ${STACK_NAME:-default from folder}):"
echo "   • Community:  $COMMUNITY_FILE"
echo "   • Stream:     $STREAM_FILE"
echo "   • Event:      $EVENT_FILE"
echo
read -p "Are you sure you want to restore from $TARGET_DATE? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo
echo "Stopping signals manager..."
$COMPOSE --profile "*" stop signals_manager

restore() {
    local name=$1
    local local_path=$2
    local container_path="/backups/$(basename "$local_path")"

    if [[ -f "$local_path" ]]; then
        echo "Restoring $name..."
        $COMPOSE run --rm --env PGPASSWORD='changeme' -v "$(pwd)/backups:/backups" database psql \
            -h 172.17.0.1 -U resonitecommunities -d resonitecommunities \
            --set ON_ERROR_STOP=off -f "$container_path"
    else
        echo "Warning: $local_path not found. Skipping $name."
    fi
}

restore "communities" "$COMMUNITY_FILE"
restore "streams" "$STREAM_FILE"
restore "events" "$EVENT_FILE"

echo
echo "Starting signals manager..."
$COMPOSE --profile "*" start signals_manager
