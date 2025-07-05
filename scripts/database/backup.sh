#!/bin/bash
set -e

BACKUP_DIR="$(pwd)/backups"
DATE=$(date +"%F_%H%M") # YYYY-MM-DD_HHMM
STACK_NAME=""
CONFIG_FILE="./stack-aliases.conf"
DRY_RUN=true
DATABASE_SERVICE_NAME="database"
DATABASE_IMAGE="postgres:16"

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Backup PostgreSQL tables using Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name or alias
  --date DATE_TIME      (optional) Override timestamp (format: YYYY-MM-DD_HHMM)
  --config FILE         (optional) Set custom config file path (default: ./stack-aliases.conf)
  --backup-dir DIR      (optional) Set custom backup directory (default: ./backups)
  --nodry               Actually execute the backup (default is dry run)
  --help                Show this help message and exit

Examples:
  $0                             Run dry backup in current folder (default stack)
  $0 --nodry                     Run actual backup
  $0 --stack prod                Use alias from config file
  $0 --stack my_stack            Use explicit stack name
  $0 --config ./my_aliases.conf  Use custom config file
  $0 --backup-dir /mnt/mybackups Use custom backup directory
EOF
}

if [[ $# -eq 0 ]]; then
    print_help
    exit 0
fi

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
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
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

echo "Using Docker Compose stack: ${STACK_NAME:-default from folder}"
echo "Backup datetime: $DATE"
$DRY_RUN && echo "Dry run mode enabled. Use --nodry to perform the backup."
echo

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Host backup directory not found: $BACKUP_DIR" >&2
    exit 1
fi
echo "Host backup directory exists: $BACKUP_DIR"
echo

STACK_PREFIX="${STACK_NAME:+${STACK_NAME}_}"

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

run $COMPOSE --profile \'*\' stop signals_manager

run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    -e PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_IP" \
    -U resonitecommunities -d resonitecommunities \
    -t community --data-only -F p \
    -f "/backups/community_${STACK_PREFIX}${DATE}.sql"

run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    -e PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_IP" \
    -U resonitecommunities -d resonitecommunities \
    -t stream --data-only -F p \
    -f "/backups/stream_${STACK_PREFIX}${DATE}.sql"

run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    -e PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_IP" \
    -U resonitecommunities -d resonitecommunities \
    -t event --data-only -F p \
    -f "/backups/event_${STACK_PREFIX}${DATE}.sql"

run $COMPOSE --profile \'*\' start signals_manager