from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import case, and_, not_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Query
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.models.signal import Event, EventStatus
from resonite_communities.utils.logger import get_logger

from resonite_communities.clients.api.routes.v2.admin import require_moderator_access

logger = get_logger(__name__)

class EventUpdateStatusRequest(BaseModel):
    id: str
    status: EventStatus


@router_v2.get("/admin/events")
async def get_admin_events(
    request: Request,
    community_id: Optional[str] = Query(None, description="Filter events by community ID"),
    platform_filter: Optional[str] = Query(None, description="Filter events by platform (e.g., 'resonite', 'vrchat', 'none', 'all')"),
    start_date: Optional[str] = Query(None, description="Filter events by starting date"),
    user_auth: UserAuthModel = Depends(require_moderator_access)
):

    custom_filters = []

    if not start_date:
        start_date = datetime.utcnow()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')

    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    custom_filters.append(
        case(
            (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
            else_=Event.start_time  # Otherwise, fallback to start_time
        ) >= start_date  # Event is considered active or upcoming if the time is greater than or equal to requested start date
    )

    if platform_filter == 'all':
        pass
    elif platform_filter == 'none':
        # Filter for events with no platform tags
        # This checks if 'resonite' or 'vrchat' are NOT in the tags
        custom_filters.append(
            and_(
                not_(Event.tags.ilike('%resonite%')),
                not_(Event.tags.ilike('%vrchat%'))
            )
        )
    elif platform_filter:
        custom_filters.append(Event.tags.ilike(f'%{platform_filter}%'))
    else:
        # Default filter: Only get Resonite events, excluding VR Chat
        custom_filters.append(
            and_(
                Event.tags.ilike('%resonite%'),
                not_(Event.tags.ilike('%vrchat%'))
            )
        )

    if community_id:
        custom_filters.append(Event.community_id == community_id)

    try:
        events = await Event().find(__order_by=['start_time'], __custom_filter=and_(*custom_filters))
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching admin events: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    events_formatted = []
    for event in events:
        events_formatted.append({
            "id": str(event.id),
            "external_id": str(event.external_id),
            "name": event.name,
            "description": event.description,
            "session_image": event.session_image,
            "location_str": event.location,
            "location_web_session_url": event.location_web_session_url,
            "location_session_url": event.location_session_url,
            "start_time": event.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": event.end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if event.end_time else None,
            "community_name": event.community.name,
            "community_url": event.community.url,
            "tags": event.tags,
            "status": event.status,
        })

    return events_formatted


@router_v2.post("/admin/events/update_status")
async def update_event_status(data: EventUpdateStatusRequest, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        result = await Event.update(
            filters=(Event.id == data.id),
            status=data.status
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating event {data.id} status: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not result:
        logger.warning(f"Event {data.id} not found for status update")
        raise HTTPException(status_code=404, detail="Event not found")

    logger.info(f"Event {data.id} status updated to {data.status}")
    return {"id": data.id, "status": data.status, "result": result}

@router_v2.delete("/admin/events/{event_id}")
async def delete_event(event_id: UUID, user_auth: UserAuthModel = Depends(require_moderator_access)):
    try:
        deleted = await Event.delete(id__eq=event_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not deleted:
        logger.warning(f"Event {event_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Event not found")

    logger.info(f"Event {event_id} deleted successfully")
    return {"id": event_id, "message": "Event deleted successfully"}
