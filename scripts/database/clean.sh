#!/bin/bash
set -e

STACK_NAME=""
BACKUP_DIR="$(pwd)/backups"
FORCE=false
CONFIG_FILE="./stack-aliases.conf"
DRY_RUN=true

print_help() {
    cat <<EOF
Usage: $0 [OPTIONS]

Truncate stream, event, and community tables in the PostgreSQL database via Docker Compose.

Options:
  --stack STACK_NAME    (optional) Specify Docker Compose project name or alias
  --config FILE         (optional) Alias config file (default: ./stack-aliases.conf)
  --backup-dir DIR      (optional) Set custom backup directory (default: ./backups)
  --force               Skip backup check and confirmation
  --nodry               Actually execute truncate (default is dry run)
  --help                Show this help message and exit

Examples:
  $0                           Dry truncate using default Compose context (current folder)
  $0 --nodry                   Actually truncate
  $0 --stack prod              Clean using an alias defined in config
  $0 --stack my_stack          Clean using a specific stack name
  $0 --force                   Force truncate without backup check
  $0 --config ./custom.conf    Use a custom alias config file
  $0 --backup-dir /mnt/mybackups Use custom backup directory for backup check
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
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
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
echo "Looking for latest backup in: $BACKUP_DIR"
$DRY_RUN && echo "Dry run mode enabled. Use --nodry to truncate."

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

run() {
    echo "+ $*"
    $DRY_RUN || eval "$@"
}

if [[ "$FORCE" != true ]]; then
    LATEST_BACKUP=$(find "$BACKUP_DIR" -type f -name "community_${STACK_PREFIX}*.sql" | sort | tail -n 1)
    if [[ ! -f "$LATEST_BACKUP" ]]; then
        echo "Error: No backup file found in $BACKUP_DIR"
        echo "Use --force to override this check."
        exit 1
    fi

    LATEST_BASENAME=$(basename "$LATEST_BACKUP")
    DATE_STR=$(echo "$LATEST_BASENAME" | sed -E "s/community_${STACK_PREFIX}([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{4})\.sql/\1 \2/")

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

    if ! $DRY_RUN; then
        read -p "Are you sure you want to truncate all data? [y/N] " CONFIRM
        [[ ! "$CONFIRM" =~ ^[Yy]$ ]] && echo "Aborted." && exit 1
    else
        echo "Dry run: skipping confirmation prompt."
    fi
else
    echo "Force mode enabled. Skipping backup age check and confirmation."
fi

run $COMPOSE --profile \'*\' stop signals_manager

run $COMPOSE run --rm \
    --env PGPASSWORD=\'changeme\' \
    database psql -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -c "'TRUNCATE TABLE stream;'"

run $COMPOSE run --rm \
    --env PGPASSWORD=\'changeme\' \
    database psql -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -c "'TRUNCATE TABLE event;'"

run $COMPOSE run --rm \
    --env PGPASSWORD=\'changeme\' \
    database psql -h 172.17.0.1 \
    -U resonitecommunities -d resonitecommunities \
    -c "'TRUNCATE TABLE stream, event, community;'"

run $COMPOSE --profile \'*\' start signals_manager
