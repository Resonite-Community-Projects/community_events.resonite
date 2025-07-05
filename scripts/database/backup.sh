#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +"%F_%H%M") # YYYY-MM-DD_HHMM
STACK_NAME=""
CONFIG_FILE="./stack-aliases.conf"
DRY_RUN=true

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Backup PostgreSQL tables using Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name or alias
  --date DATE_TIME      (optional) Override timestamp (format: YYYY-MM-DD_HHMM)
  --config FILE         (optional) Set custom config file path (default: ./stack-aliases.conf)
  --nodry               Actually execute the backup (default is dry run)
  --help                Show this help message and exit

Examples:
  $0                             Run dry backup in current folder (default stack)
  $0 --nodry                     Run actual backup
  $0 --stack prod                Use alias from config file
  $0 --stack my_stack            Use explicit stack name
  $0 --config ./my_aliases.conf  Use custom config file
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

run() {
    echo "+ $*"
    $DRY_RUN || eval "$@"
}

run $COMPOSE --profile \'*\' stop signals_manager

run $COMPOSE run --rm \
    --env PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    database pg_dump -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -t community --data-only -F p \
    -f "/backups/community_${STACK_PREFIX}${DATE}.sql"

run $COMPOSE run --rm \
    --env PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    database pg_dump -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -t stream --data-only -F p \
    -f "/backups/stream_${STACK_PREFIX}${DATE}.sql"

run $COMPOSE run --rm \
    --env PGPASSWORD='changeme' \
    -v "$BACKUP_DIR:/backups" \
    database pg_dump -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -t event --data-only -F p \
    -f "/backups/event_${STACK_PREFIX}${DATE}.sql"

run $COMPOSE --profile \'*\' start signals_manager
