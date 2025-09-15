from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.models.community import Community, events_platforms

@router_v2.get("/communities")
async def get_communities():
    communities = await Community().find(platform__in=events_platforms)

    communities_formated = []
    for community in communities:
        communities_formated.append({
            "id": community.id,
            "name": community.name,
            "description": community.custom_description if community.custom_description else community.default_description,
            "url": community.url,
            "icon": community.logo,
            "external_id": community.external_id,
            "platform": community.platform,
            "public": True if 'public' in community.tags else False,
            "configured": community.configured,
        })
    return communities_formated

@router_v2.get("/communities/{community_id}")
async def get_community(community_id: str):
    try:
        community = (await Community().find(id=community_id))[0]
    except IndexError:
        return {}

    return {
        "id": community.id,
        "name": community.name,
        "description": community.custom_description if community.custom_description else community.default_description,
        "url": community.url,
        "icon": community.logo,
        "external_id": community.external_id,
        "platform": community.platform,
        "public": True if 'public' in community.tags else False,
        "configured": community.configured,
    }
