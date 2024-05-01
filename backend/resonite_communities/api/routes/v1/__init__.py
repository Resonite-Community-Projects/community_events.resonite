from resonite_communities.api.utils import VersionedAPIRouter, get_route_version_modules

router = VersionedAPIRouter(version="1.0")
for module in get_route_version_modules(__name__, __file__):
    router.include_router(module.router)
