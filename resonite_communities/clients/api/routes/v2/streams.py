from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.models.signal import Stream
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from fastapi import Depends
from datetime import datetime, timedelta

@router_v2.get("/streams")
async def get_streams_v2(user_auth: UserAuthModel = Depends(get_user_auth)):

    streams = await Stream().find(
        __order_by=['start_time'],
        end_time__gtr_eq=datetime.utcnow(),
        end_time__less=datetime.utcnow() + timedelta(days=8)
    )

    streams_formatted = []
    for stream in streams:
        streams_formatted.append({
            "id": str(stream.id),
            "external_id": str(stream.external_id),
            "name": stream.name,
            "start_time": stream.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_time": stream.end_time.strftime("%Y-%m-%dT%H:%M:%SZ") if stream.end_time else None,
            "community_name": stream.community.name if stream.community else None,
            "community_url": stream.community.url if stream.community else None,
            "community_logo": stream.community.logo if stream.community else None,
            "tags": stream.tags,
            "status": stream.status,
        })

    return streams_formatted
