import json
from datetime import datetime
from dacite.types import is_instance
from fastapi import Depends, Response, HTTPException
from sqlalchemy import and_, not_, case, or_
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.models.community import Community

from resonite_communities.utils.config import ConfigManager

from resonite_communities.utils.tools import is_local_env
from resonite_communities.clients.utils.auth import UserAuthModel


config_manager = ConfigManager()

from enum import Enum

class FormatType(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"

separators = {
    "v1": {"field": "`", "object": "\n"},
    "v2": {"field": chr(30), "object": chr(29)},
}

def clean_text(text):
    """ Remove all invalid characters for text_dumps. """
    if text:
        text = text.replace('`', ' ')
        text = text.replace('\n\n', ' ')
        text = text.replace('\n\r', ' ')
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
    else:
        text = ''
    return text

def text_dumps(events, version):
    """ Convert the Python Dictionary to a text string. """

    if version not in separators:
        raise ValueError("Unsported version.")
    field_separator = separators[version]['field']
    object_separator = separators[version]['object']

    formatted_items = []
    for event in events:
        formatted_event_values = []
        for event_key, event_value in event.items():

            # Convert list to a more usable text format
            if isinstance(event_value, list):
                event_value = ",".join(map(str, event_value))

            # Dict are not supported in TEXT format, silently pass to the next
            elif is_instance(event_value, dict):
                continue

            # Clean some event key of non wanted chars for the v1
            elif event_key in ['description'] and version == "v1":
                event_value = clean_text(event_value)

            # By default we convert anything else to string
            else:
                event_value = str(event_value)
            formatted_event_values.append(event_value)
        formatted_items.append(field_separator.join(formatted_event_values))
    return object_separator.join(formatted_items)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def set_default_format(
    version: str = "v1",
    format_type: FormatType | None = None,
):
    if not format_type:
        match version:
            case "v1":
                format_type = FormatType.TEXT
            case _:
                format_type = FormatType.JSON
    else:
        format_type = FormatType(format_type)

    return format_type

async def get_filtered_events(
    host: str,
    version: str,
    communities: str,
    user_auth: UserAuthModel = None,
):
    signals = []

    communities_filter = True
    if communities:
        communities = [community for community in communities.split(",")]
        communities_filter = Event.community.has(Community.name.in_(communities))

    if isinstance(config_manager.infrastructure_config.PUBLIC_DOMAIN, str):
        public_domains = [config_manager.infrastructure_config.PUBLIC_DOMAIN]
    else:
        public_domains = config_manager.infrastructure_config.PUBLIC_DOMAIN

    if isinstance(config_manager.infrastructure_config.PRIVATE_DOMAIN, str):
        private_domains = [config_manager.infrastructure_config.PRIVATE_DOMAIN]
    else:
        private_domains = config_manager.infrastructure_config.PRIVATE_DOMAIN

    if host not in public_domains and host not in private_domains:
        msg = f"Unsupported domain: {host}."
        if is_local_env:
            msg += " You need to configure your hosts file for access to the locally to the HTTP API."
            msg += " See https://docs.resonite-communities.com/DeveloperGuide/server-configuration/"
        raise HTTPException(status_code=400, detail=msg)

    if host in private_domains:
        visibility_filter = True
    elif user_auth and user_auth.is_superuser:
        visibility_filter = True
    elif user_auth:
        visibility_filter = or_(
            not_(Event.tags.ilike('%private%')),  # All public events
            and_(  # Private events that the user has access to
                Event.tags.ilike('%private%'),
                Event.community_id.in_(user_auth.discord_account.user_communities)
            )
        )
    else:
        visibility_filter = not_(Event.tags.ilike("%private%"))

    # Only get Resonite events
    platform_filter = and_(
        Event.tags.ilike('%resonite%'),
        not_(Event.tags.ilike('%vrchat%'))
    )

    # Only get Events that are ACTIVE or READY
    status_filter = Event.status.in_((EventStatus.ACTIVE, EventStatus.READY))

    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now
    custom_filter=and_(communities_filter, visibility_filter, platform_filter, status_filter, time_filter)

    # TODO: Instead of extend the signals variable, the Event and Stream find command should be one
    # SQL commend, optimization to order elements by date
    signals.extend(await Event.find(__custom_filter=custom_filter, __order_by=["start_time"]))

    versioned_events = []
    for signal in signals:
        if version == "v1":
            versioned_events.append({
                "name": signal.name,
                #"description": signal.custom_description if signal.custom_description else signal.default_description,
                "description": signal.description,
                "location_str": signal.location,
                "start_time": signal.start_time.strftime("%Y/%m/%d %H:%M:%S+00:00"),
                "end_time": signal.end_time.strftime("%Y/%m/%d %H:%M:%S+00:00") if signal.end_time else None,
                "community_name": signal.community.name, # TODO: Connect this to a session
            })
        elif version == "v2":
            versioned_events.append({
                "id": str(signal.id),
                "external_id": str(signal.external_id),
                "name": signal.name,
                #"description": signal.custom_description if signal.custom_description else signal.default_description,
                "description": signal.description,
                "session_image": signal.session_image,
                "location_str": signal.location,
                "location_web_session_url": signal.location_web_session_url,
                "location_session_url": signal.location_session_url,
                "start_time": signal.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": signal.end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if signal.end_time else None,
                "community_name": signal.community.name, # TODO: Connect this to a session
                "community_url": signal.community.url,
                "tags": signal.tags,
                "status": signal.status,
                # source
            })
        else:
            raise HTTPException(status_code=400, detail="Unsupported version")

    return versioned_events

def generate_events_response(
        version: str,
        format_type: FormatType = Depends(set_default_format),
        events: list[dict] = Depends(get_filtered_events),
):
    match format_type:
        case FormatType.TEXT:
            return Response(
                text_dumps(events, version),
                media_type="text/plain",
            )
        case FormatType.JSON:
            return Response(
                json.dumps(events, cls=JSONEncoder),
                media_type="application/json",
            )
        case _:
            raise HTTPException(status_code=400, detail="Unsupported format")
