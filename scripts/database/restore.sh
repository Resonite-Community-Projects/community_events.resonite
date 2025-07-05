#!/bin/bash
set -e

BACKUP_DIR="./backups"
TARGET_DATE=""
STACK_NAME=""
CONFIG_FILE="./stack-aliases.conf"
DRY_RUN=true

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Restore PostgreSQL backups using Docker Compose.

Options:
  --date TIMESTAMP       Restore from specific backup timestamp (e.g. 2025-07-03_1645)
  --date latest          Restore from the latest available backup
  --stack STACK_NAME     Specify Docker Compose project name or alias
  --config FILE          (optional) Alias config file (default: ./stack-aliases.conf)
  --list                 List all available backup timestamps
  --nodry                Actually perform restore (default is dry run)
  --help                 Show this help message and exit

Examples:
  $0 --date latest
  $0 --nodry --date latest
  $0 --stack prod --date 2025-07-03_1645
  $0 --stack my_stack --nodry --date latest
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
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --list)
            echo "Available backup timestamps:"
            find "$BACKUP_DIR" -type f -name '*.sql' \
                | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}' \
                | sort -u
            exit 0
            ;;
        --nodry)
            DRY_RUN=false
            shift
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
    [[ -n "$ALIAS_VALUE" ]] && STACK_NAME="$ALIAS_VALUE"
fi

COMPOSE="docker compose"
[[ -n "$STACK_NAME" ]] && COMPOSE+=" -p $STACK_NAME"
STACK_PREFIX="${STACK_NAME:+${STACK_NAME}_}"

if [[ "$TARGET_DATE" == "latest" || -z "$TARGET_DATE" ]]; then
    TARGET_DATE=$(find "$BACKUP_DIR" -type f -name "community_${STACK_PREFIX}*.sql" \
        | sed -E "s|.*community_${STACK_PREFIX}([0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4})\.sql|\1|" \
        | sort -u | tail -n 1)
    [[ -z "$TARGET_DATE" ]] && echo "No backup files found for community in $BACKUP_DIR" && exit 1
    echo "Using latest backup date based on community: $TARGET_DATE"
fi

COMMUNITY_FILE="$BACKUP_DIR/community_${STACK_PREFIX}${TARGET_DATE}.sql"
STREAM_FILE="$BACKUP_DIR/stream_${STACK_PREFIX}${TARGET_DATE}.sql"
EVENT_FILE="$BACKUP_DIR/event_${STACK_PREFIX}${TARGET_DATE}.sql"

echo
echo "The following backup files will be restored (stack: ${STACK_NAME:-default from folder}):"
echo "   • Community:  $COMMUNITY_FILE"
echo "   • Stream:     $STREAM_FILE"
echo "   • Event:      $EVENT_FILE"
# The dry run message should always be displayed if DRY_RUN is true.
if $DRY_RUN; then
    echo "Dry run mode enabled. Use --nodry to apply restore."
fi
echo

run() {
    echo "+ $*"
    $DRY_RUN || eval "$@"
}

if ! $DRY_RUN; then
    read -p "Are you sure you want to truncate all data? [y/N] " CONFIRM
    [[ ! "$CONFIRM" =~ ^[Yy]$ ]] && echo "Aborted." && exit 1
else
    echo "Dry run: skipping confirmation prompt."
fi

run $COMPOSE --profile \'*\' stop signals_manager

restore() {
    local name=$1
    local local_path=$2
    local container_path="/backups/$(basename "$local_path")"
    if [[ -f "$local_path" ]]; then
        run $COMPOSE run --rm \
            --env PGPASSWORD='changeme' \
            -v "$(pwd)/backups:/backups" \
            database psql \
            -h 172.17.0.1 \
            -U resonitecommunities \
            -d resonitecommunities \
            --set ON_ERROR_STOP=off \
            -f "$container_path"
    else
        echo "Warning: $local_path not found. Skipping $name."
    fi
}

restore "communities" "$COMMUNITY_FILE"
restore "streams" "$STREAM_FILE"
restore "events" "$EVENT_FILE"

run $COMPOSE --profile \'*\' start signals_manager