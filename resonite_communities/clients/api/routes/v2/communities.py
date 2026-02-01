from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.models.community import Community, events_platforms, CommunityPlatform
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from fastapi import Depends

@router_v2.get("/communities")
async def get_communities(
    platform: str = "events",
    configured_only: bool = False,
    public_only: bool = False,
    user_communities_only: bool = False,
    include_all: bool = False,
    user_auth: UserAuthModel = Depends(get_user_auth)
):
    filters = {}

    if not include_all:
        if platform.lower() in ["streams", "twitch"]:
            filters['platform__in'] = [CommunityPlatform.TWITCH]
        elif platform.lower() == "events" or platform == "":
            # "events" is the default, "" is for backward compatibility
            filters['platform__in'] = events_platforms
        else:
            filters['platform__in'] = events_platforms

    if configured_only:
        filters['configured__eq'] = True

    if user_communities_only and user_auth:
        filters['id__in'] = user_auth.discord_account.user_communities

    if public_only:
        filters['__custom_filter'] = Community.tags.ilike('%public%')

    communities = await Community().find(**filters)

    communities_formatted = []
    for community in communities:
        communities_formatted.append({
            "id": community.id,
            "name": community.name,
            "description": community.custom_description if community.custom_description else community.default_description,
            "default_description": community.default_description,
            "monitored": community.monitored,
            "members_count": community.members_count,
            "url": community.url,
            "icon": community.logo,
            "external_id": community.external_id,
            "platform": community.platform,
            "public": True if 'public' in (community.tags or []) else False,
            "configured": community.configured,
        })
    return communities_formatted

@router_v2.get("/communities/{community_id}")
async def get_community(community_id: str):
    try:
        community = (await Community().find(id=community_id))[0]
    except IndexError:
        return {}

    return {
        "id": community.id,
        "name": community.name,
        "icon": community.logo,
        "description": community.custom_description if community.custom_description else community.default_description,
        "default_description": community.default_description,
        "monitored": community.monitored,
        "members_count": community.members_count,
        "url": community.url,
        "tags": community.tags,
        "languages": community.languages,
        "external_id": community.external_id,
        "platform": community.platform,
        "public": True if 'public' in community.tags else False,
        "configured": community.configured,
    }
