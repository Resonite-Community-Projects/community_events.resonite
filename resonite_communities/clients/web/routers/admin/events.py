from copy import deepcopy
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse
from sqlalchemy import case, and_

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import Event
from resonite_communities.utils import Config

router = APIRouter()

@router.get("/admin/events")
async def get_communities(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    # Only get Resonite events
    platform_filter = Event.tags.ilike('%resonite%')

    # Determine if an event is either active or upcoming by comparing end_time or start_time with the current time.
    # If end_time is available, it will be used; otherwise, fallback to start_time.
    time_filter = case(
        (Event.end_time.isnot(None), Event.end_time),  # Use end_time if it's not None
        else_=Event.start_time  # Otherwise, fallback to start_time
    ) >= datetime.utcnow()  # Event is considered active or upcoming if the time is greater than or equal to now


    events = Event().find(__order_by=['start_time'], __custom_filter=and_(time_filter, platform_filter))
    #events = Event().find(__order_by=['start_time'], __custom_filter=platform_filter)

    try:
        api_url = Config.PUBLIC_DOMAIN[0]
    except KeyError:
        api_url = None

    if api_url and api_url.endswith(".local"):
        api_url = f"http://{api_url}"
    else:
        api_url = f"https://{api_url}"

    return templates.TemplateResponse("admin/events.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "api_url": Config.PUBLIC_DOMAIN,
        "events": events,
        "request": request,
    })

