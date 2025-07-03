#!/bin/bash
set -e

STACK_NAME=""
BACKUP_DIR="./backups"
FORCE=false

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Truncate stream, event, and community tables in the PostgreSQL database via Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name
  --force               Skip backup check and confirmation
  --help                Show this help message and exit

Examples:
  $0                         Clean using default Compose context (current folder)
  $0 --stack my_stack        Clean using a specific stack/project name
  $0 --force                 Force truncate without backup check
EOF
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --stack)
            STACK_NAME="$2"
            shift 2
            ;;
        --force)
            FORCE=true
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

COMPOSE="docker compose"
[[ -n "$STACK_NAME" ]] && COMPOSE+=" -p $STACK_NAME"

echo "Using Docker Compose stack: ${STACK_NAME:-default from folder}"
echo "Looking for latest backup in: $BACKUP_DIR"

if [[ "$FORCE" != true ]]; then
    LATEST_BACKUP=$(find "$BACKUP_DIR" -type f -name "community_*.sql" | sort | tail -n 1)

    if [[ ! -f "$LATEST_BACKUP" ]]; then
        echo "Error: No backup file found in $BACKUP_DIR"
        echo "Use --force to override this check."
        exit 1
    fi

    LATEST_BASENAME=$(basename "$LATEST_BACKUP")
    DATE_STR=$(echo "$LATEST_BASENAME" | sed -E 's/community_([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{4})\.sql/\1 \2/')

    # Convert to UNIX timestamp
    BACKUP_TIMESTAMP=$(date -d "${DATE_STR:0:10} ${DATE_STR:11:2}:${DATE_STR:13:2}" +%s)
    NOW_TIMESTAMP=$(date +%s)
    AGE_SECONDS=$((NOW_TIMESTAMP - BACKUP_TIMESTAMP))

    if (( AGE_SECONDS > 86400 )); then
        echo "Error: Last backup is older than 24 hours ($((AGE_SECONDS / 3600)) hours ago)."
        echo "Refusing to truncate unless --force is used."
        exit 1
    fi

    echo "Backup found: $LATEST_BACKUP"
    echo "Age: $((AGE_SECONDS / 60)) minutes"
    read -p "Are you sure you want to truncate all data? [y/N] " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "Force mode enabled. Skipping backup age check and confirmation."
fi

echo
echo "Stop signals manager"
$COMPOSE --profile "*" stop signals_manager

echo "Clean streams..."
$COMPOSE run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities \
  -c "TRUNCATE TABLE stream;"

echo "Clean events..."
$COMPOSE run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities \
  -c "TRUNCATE TABLE event;"

echo "Clean communities (including stream and event)..."
$COMPOSE run --rm --env PGPASSWORD='changeme' database psql \
  -h 172.17.0.1 -U resonitecommunities -d resonitecommunities \
  -c "TRUNCATE TABLE stream, event, community;"

echo "Start signals manager"
$COMPOSE --profile "*" start signals_manager
