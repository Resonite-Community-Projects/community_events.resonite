#!/bin/bash
set -e

BACKUP_DIR="$(pwd)/backups"
DATE=$(date +"%F_%H%M") # YYYY-MM-DD_HHMM
STACK_NAME_ALIAS="" # This will store the user-provided alias (e.g., "prod")
RESOLVED_STACK_NAME="" # This will store the actual Docker Compose project name (e.g., "prod_community_eventsresonite")
CONFIG_FILE="./stack-aliases.conf" # For Docker Compose stack aliases AND app config paths
APP_CONFIG_FILE="" # This will be derived from CONFIG_FILE based on STACK_NAME_ALIAS
DRY_RUN=true
DATABASE_SERVICE_NAME="database"
DATABASE_IMAGE="postgres:16"

# Database credentials (to be parsed from APP_CONFIG_FILE)
DB_USER=""
DB_PASSWORD=""
DB_NAME=""
DB_HOST=""
DB_PORT=""

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
Usage: $0 --stack STACK_NAME [OPTIONS]

Backup PostgreSQL tables using Docker Compose.

Options:
  --stack STACK_NAME    (mandatory) Specify Docker Compose project name alias (e.g., 'prod', 'dev')
  --date DATE_TIME      (optional) Override timestamp (format: YYYY-MM-DD_HHMM)
  --config FILE         (optional) Set custom config file path (default: ./stack-aliases.conf)
  --backup-dir DIR      (optional) Set custom backup directory (default: ./backups)
  --nodry               Actually execute the backup (default is dry run)
  --help                Show this help message and exit

Examples:
  $0 --stack prod              Run dry backup for 'prod' stack, deriving app config from aliases file
  $0 --stack dev --nodry       Run actual backup for 'dev' stack
  $0 --config ./my_aliases.conf --stack my_custom_stack
EOF
}

if [[ $# -eq 0 ]]; then
    print_help
    exit 0
fi

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --stack)
            STACK_NAME_ALIAS="$2"
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

if [[ -z "$STACK_NAME_ALIAS" ]]; then
    echo "Error: --stack STACK_NAME is a mandatory argument." >&2
    print_help
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file not found: $CONFIG_FILE" >&2
    exit 1
fi

RESOLVED_STACK_NAME=$(grep -E "^${STACK_NAME_ALIAS}=" "$CONFIG_FILE" | cut -d'=' -f2-)
if [[ -z "$RESOLVED_STACK_NAME" ]]; then
    echo "Error: Stack alias '$STACK_NAME_ALIAS' not found in $CONFIG_FILE." >&2
    exit 1
fi
echo "Resolved Docker Compose stack alias '$STACK_NAME_ALIAS' to project name '$RESOLVED_STACK_NAME'"

APP_CONFIG_FILE_KEY="${STACK_NAME_ALIAS}_app_config"
APP_CONFIG_FILE=$(grep -E "^${APP_CONFIG_FILE_KEY}=" "$CONFIG_FILE" | cut -d'=' -f2-)

if [[ -z "$APP_CONFIG_FILE" ]]; then
    echo "Error: Application config file mapping for '${STACK_NAME_ALIAS}' (key: '${APP_CONFIG_FILE_KEY}') not found in $CONFIG_FILE." >&2
    echo "Please ensure an entry like '${APP_CONFIG_FILE_KEY}=/path/to/your/app_config.toml' exists in your config file." >&2
    exit 1
fi
echo "Resolved application config file: $APP_CONFIG_FILE"

parse_database_url() {
    local config_file="$1"
    if [[ ! -f "$config_file" ]]; then
        echo "Error: Application configuration TOML file not found: $config_file" >&2
        exit 1
    fi

    echo "Parsing DATABASE_URL from TOML file: $config_file"

    local db_url_line=$(grep -E '^DATABASE_URL\s*=' "$config_file" | grep -v '^#' | head -n 1)

    if [[ -z "$db_url_line" ]]; then
        echo "Error: 'DATABASE_URL' not found or is commented out in $config_file." >&2
        echo "Expected format: DATABASE_URL = \"your_url\"" >&2
        exit 1
    fi

    local db_url=$(echo "$db_url_line" | sed -E 's/^DATABASE_URL\s*=\s*"([^"]*)".*$/\1/')

    if [[ -z "$db_url" ]]; then
        echo "Error: Extracted DATABASE_URL is empty or not properly quoted in '$db_url_line'." >&2
        echo "Ensure DATABASE_URL is defined as 'DATABASE_URL = \"value\"'." >&2
        exit 1
    fi

    local parsed_output
    if ! parsed_output=$(echo "$db_url" | sed -E 's/^postgresql:\/\/(([^:]+)(:([^@]+))?@)?([^:]+)(:([0-9]+))?\/([^\?]+).*$/\2 \4 \5 \7 \8/'); then
         echo "Error: sed failed to process DATABASE_URL string '$db_url'." >&2
         exit 1
    fi
    IFS=' ' read -r DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME <<< "$parsed_output"

    if [[ -z "$DB_USER" ]]; then
        echo "Error: Database user not found in DATABASE_URL." >&2
        exit 1
    fi
    if [[ -z "$DB_HOST" || -z "$DB_NAME" ]]; then
        echo "Error: Could not extract all required components (host, db name) from DATABASE_URL. Check regex or URL format." >&2
        exit 1
    fi

    echo "  DB User: $DB_USER"
    echo "  DB Host: $DB_HOST"
    echo "  DB Port: $DB_PORT"
    echo "  DB Name: $DB_NAME"
    [[ -n "$DB_PASSWORD" ]] && echo "  DB Password: (present)" || echo "  DB Password: (not present/empty)"
    echo
}

parse_database_url "$APP_CONFIG_FILE"

STACK_NAME="$RESOLVED_STACK_NAME"
COMPOSE="docker compose"
COMPOSE+=" -p $STACK_NAME"

echo "Using Docker Compose stack: $STACK_NAME"
echo "Backup datetime: $DATE"
$DRY_RUN && echo "Dry run mode enabled. Use --nodry to perform the backup."
echo

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Host backup directory not found: $BACKUP_DIR" >&2
    exit 1
fi
echo "Host backup directory exists: $BACKUP_DIR"
echo

STACK_PREFIX="${STACK_NAME}_"

DETECTED_PROJECT_NAME="$STACK_NAME"

echo "Verifying if Docker Compose stack '$DETECTED_PROJECT_NAME' has previously run containers..."
if [[ -z "$(docker ps -a --filter label=com.docker.compose.project="$DETECTED_PROJECT_NAME" --format '{{.ID}}')" ]]; then
    ERROR_MESSAGE="Error: Docker Compose stack '$DETECTED_PROJECT_NAME' does not appear to have any containers created by it."
    ERROR_MESSAGE+="\n  This means no containers exist for the resolved stack name '$STACK_NAME' (requested via alias '$STACK_NAME_ALIAS')."
    ERROR_MESSAGE+="\n\nPlease ensure:"
    ERROR_MESSAGE+="\n  1. The --stack alias '$STACK_NAME_ALIAS' is correct and resolves to '$STACK_NAME'."
    ERROR_MESSAGE+="\n  2. The Docker Compose stack has been brought up at least once (e.g., 'docker compose up -d') with this project name."
    echo -e "$ERROR_MESSAGE"
    exit 1
fi
echo "Docker Compose stack '$DETECTED_PROJECT_NAME' found with associated containers."

# If DB_HOST was resolved from APP_CONFIG_FILE as "database" (the service name),
# then we proceed with discovering the container and its IP within the Docker Compose project network.
# If DB_HOST was a specific IP/hostname, we assume it's directly reachable.
# We will still use a network from the detected stack for 'docker run --network'.
if [[ "$DB_HOST" == "$DATABASE_SERVICE_NAME" ]]; then
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
    DB_IP_FROM_INSPECT=""

    NETWORK_ENTRIES=$(echo "$NETWORK_INFO" | jq -c 'to_entries[]')

    while IFS= read -r entry; do
        CURRENT_NET_NAME=$(echo "$entry" | jq -r '.key')
        CURRENT_NET_IP=$(echo "$entry" | jq -r '.value.IPAddress // empty')

        if [[ -n "$CURRENT_NET_IP" ]]; then
            DB_NETWORK_NAME="$CURRENT_NET_NAME"
            DB_IP_FROM_INSPECT="$CURRENT_NET_IP"
            break
        fi
    done <<< "$NETWORK_ENTRIES"

    if [[ -z "$DB_NETWORK_NAME" ]]; then
        echo "Error: Could not determine an active network with an IP address for container '$DB_CONTAINER_FULL_NAME'."
        echo "Ensure the container is running and connected to a network."
        exit 1
    fi

    echo "Detected database container network: $DB_NETWORK_NAME"
    echo "Detected database container IP: $DB_IP_FROM_INSPECT (direct inspection)"

    RESOLVED_DB_IP=$(docker run --rm --network "$DB_NETWORK_NAME" alpine ash -c "ping -c 1 $DATABASE_SERVICE_NAME | head -n 1 | awk '{print \$3}' | sed 's/[():]//g'")

    if [[ -z "$RESOLVED_DB_IP" ]]; then
        echo "Warning: Could not resolve IP address for '$DATABASE_SERVICE_NAME' service name within network '$DB_NETWORK_NAME'."
        echo "Falling back to directly inspected IP: $DB_IP_FROM_INSPECT"
        DB_HOST_FOR_PGDUMP="$DB_IP_FROM_INSPECT" # Use inspected IP
    else
        DB_HOST_FOR_PGDUMP="$RESOLVED_DB_IP" # Use DNS-resolved IP
        echo "Resolved database service IP via network DNS: $DB_HOST_FOR_PGDUMP"
    fi
else
    # If DB_HOST was not "database", assume it's an external host or a host directly reachable.
    # We still need a network for 'docker run --network'. Pick the first one from the detected project.
    echo "Using DB_HOST from app config: $DB_HOST (assuming external or directly resolvable)"
    DB_HOST_FOR_PGDUMP="$DB_HOST"

    DB_NETWORK_NAME=$(docker ps -a \
        --filter label=com.docker.compose.project="$DETECTED_PROJECT_NAME" \
        --format '{{.Networks}}' | head -n 1 | cut -d',' -f1) # Just pick the first network if multiple

    if [[ -z "$DB_NETWORK_NAME" ]]; then
        echo "Warning: Could not detect a Docker network for stack '$DETECTED_PROJECT_NAME'."
        echo "This might cause connection issues if '$DB_HOST_FOR_PGDUMP' is a Docker internal hostname but no network is available."
    else
        echo "Will attempt to use Docker network: $DB_NETWORK_NAME for external host connection."
    fi
fi

echo

run() {
    echo "+ $*"
    $DRY_RUN || eval "$@"
}

run $COMPOSE --profile \'*\' stop signals_manager

# Use parsed credentials for pg_dump
PGPASSWORD_ENV="-e PGPASSWORD='$DB_PASSWORD'"
if [[ -z "$DB_PASSWORD" ]]; then
    PGPASSWORD_ENV="" # Do not pass PGPASSWORD if it's empty
    echo "Warning: PGPASSWORD is empty. pg_dump might prompt for a password."
fi

echo "Running pg_dump commands..."
run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    $PGPASSWORD_ENV \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_HOST_FOR_PGDUMP" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -t community --data-only -F p \
    -f "/backups/community_${STACK_PREFIX}${DATE}.sql"

run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    $PGPASSWORD_ENV \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_HOST_FOR_PGDUMP" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -t stream --data-only -F p \
    -f "/backups/stream_${STACK_PREFIX}${DATE}.sql"

run docker run --rm \
    --network "$DB_NETWORK_NAME" \
    $PGPASSWORD_ENV \
    -v "$BACKUP_DIR:/backups" \
    "$DATABASE_IMAGE" \
    pg_dump -h "$DB_HOST_FOR_PGDUMP" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" \
    -t event --data-only -F p \
    -f "/backups/event_${STACK_PREFIX}${DATE}.sql"

run $COMPOSE --profile \'*\' start signals_manager