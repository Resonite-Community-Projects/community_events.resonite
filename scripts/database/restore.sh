#!/bin/bash
set -e

BACKUP_DIR="$(pwd)/backups"
TARGET_DATE=""
STACK_NAME=""
CONFIG_FILE="./stack-aliases.conf"
DRY_RUN=true
DATABASE_SERVICE_NAME="database"
DATABASE_IMAGE="postgres:16"

check_jq_installed() {
    if ! command -v jq &> /dev/null; then
        echo "Error: 'jq' is not installed." >&2
        echo "The 'jq' utility is required for this script to parse JSON output from Docker." >&2
        echo "" >&2
        exit 1
    fi
}

check_jq_installed

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Restore PostgreSQL backups using Docker Compose.

Options:
  --date TIMESTAMP       Restore from specific backup timestamp (e.g. 2025-07-03_1645)
  --date latest          Restore from the latest available backup
  --stack STACK_NAME     Specify Docker Compose project name or alias
  --config FILE          (optional) Alias config file (default: ./stack-aliases.conf)
  --backup-dir DIR       (optional) Set custom backup directory (default: ./backups)
  --list                 List all available backup timestamps
  --nodry                Actually perform restore (default is dry run)
  --help                 Show this help message and exit

Examples:
  $0 --date latest
  $0 --nodry --date latest
  $0 --stack prod --date 2025-07-03_1645
  $0 --stack my_stack --nodry --date latest
  $0 --list
  $0 --backup-dir /mnt/mybackups --date latest
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
        --backup-dir)
            BACKUP_DIR="$2"
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
    ORIGINAL_STACK_NAME="$STACK_NAME" # Store user-provided name
    ALIAS_VALUE=$(grep "^$STACK_NAME=" "$CONFIG_FILE" | cut -d'=' -f2-)
    if [[ -n "$ALIAS_VALUE" ]]; then
        echo "Resolved stack alias '$STACK_NAME' to '$ALIAS_VALUE'"
        STACK_NAME="$ALIAS_VALUE"
        USING_ALIAS=true # Set alias flag
    fi
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

DETECTED_PROJECT_NAME="$STACK_NAME"
if [[ -z "$DETECTED_PROJECT_NAME" ]]; then
    DETECTED_PROJECT_NAME=$(basename "$(pwd)")
    DETECTED_PROJECT_NAME=${DETECTED_PROJECT_NAME//-/_}
fi

echo "Verifying if Docker Compose stack '$DETECTED_PROJECT_NAME' has previously run containers..."
if [[ -z "$(docker ps -a --filter label=com.docker.compose.project="$DETECTED_PROJECT_NAME" --format '{{.ID}}')" ]]; then
    ERROR_MESSAGE="Error: Docker Compose stack '$DETECTED_PROJECT_NAME' does not appear to have any containers created by it."
    if $USING_ALIAS; then
        ERROR_MESSAGE+="\n  This means no containers exist for the resolved stack name '$STACK_NAME' (requested via alias '$ORIGINAL_STACK_NAME')."
    elif [[ -n "$STACK_NAME" ]]; then
        ERROR_MESSAGE+="\n  This means no containers exist for the specified stack name '$STACK_NAME'."
    else
        ERROR_MESSAGE+="\n  This means no containers exist for the default stack name (derived from current directory: '$DETECTED_PROJECT_NAME')."
    fi
    ERROR_MESSAGE+="\n\nPlease ensure:"
    ERROR_MESSAGE+="\n  1. You are in the correct directory if not using --stack."
    ERROR_MESSAGE+="\n  2. The --stack name or alias is correct and matches a previously (or currently) running Compose project."
    ERROR_MESSAGE+="\n  3. The Docker Compose stack has been brought up at least once (e.g., 'docker compose up -d')."
    echo -e "$ERROR_MESSAGE"
    exit 1
fi
echo "Docker Compose stack '$DETECTED_PROJECT_NAME' found with associated containers."

DB_CONTAINER_FULL_NAME=$(docker ps -a \
    --filter label=com.docker.compose.project="$DETECTED_PROJECT_NAME" \
    --filter label=com.docker.compose.service="$DATABASE_SERVICE_NAME" \
    --format '{{.Names}}' | head -n 1)

if [[ -z "$DB_CONTAINER_FULL_NAME" ]]; then
    echo "Error: Could not find a container for service '$DATABASE_SERVICE_NAME' in stack '$DETECTED_PROJECT_NAME'."
    echo "Please ensure the service name is correct and it has been brought up at least once."
    exit 1
fi
echo "Found database container: $DB_CONTAINER_FULL_NAME"

DB_CONTAINER_ID=$(docker inspect -f '{{.Id}}' "$DB_CONTAINER_FULL_NAME")

NETWORK_INFO=$(docker inspect -f '{{json .NetworkSettings.Networks}}' "$DB_CONTAINER_ID")

DB_NETWORK_NAME=""
DB_IP=""

NETWORK_ENTRIES=$(echo "$NETWORK_INFO" | jq -c 'to_entries[]')

while IFS= read -r entry; do
    CURRENT_NET_NAME=$(echo "$entry" | jq -r '.key')
    CURRENT_NET_IP=$(echo "$entry" | jq -r '.value.IPAddress // empty')

    if [[ -n "$CURRENT_NET_IP" ]]; then
        DB_NETWORK_NAME="$CURRENT_NET_NAME"
        DB_IP="$CURRENT_NET_IP"
        break
    fi
done <<< "$NETWORK_ENTRIES"

if [[ -z "$DB_NETWORK_NAME" ]]; then
    echo "Error: Could not determine an active network with an IP address for container '$DB_CONTAINER_FULL_NAME'."
    echo "Ensure the container is running and connected to a network."
    exit 1
fi

echo "Detected database container network: $DB_NETWORK_NAME"
echo "Detected database container IP: $DB_IP (direct inspection)"

RESOLVED_DB_IP=$(docker run --rm --network "$DB_NETWORK_NAME" alpine ash -c "ping -c 1 $DATABASE_SERVICE_NAME | head -n 1 | awk '{print \$3}' | sed 's/[():]//g'")

if [[ -z "$RESOLVED_DB_IP" ]]; then
    echo "Warning: Could not resolve IP address for '$DATABASE_SERVICE_NAME' service name within network '$DB_NETWORK_NAME'."
    echo "Falling back to directly inspected IP: $DB_IP"
else
    DB_IP="$RESOLVED_DB_IP"
    echo "Resolved database service IP via network DNS: $DB_IP"
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
        run docker run --rm \
            --network "$DB_NETWORK_NAME" \
            -e PGPASSWORD='changeme' \
            -v "$BACKUP_DIR:/backups" \
            "$DATABASE_IMAGE" \
            psql \
            -h "$DB_IP" \
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