from resonite_communities.clients.api.utils.versioning import VersionedAPIRouter

router_v1 = VersionedAPIRouter(version="1.0")
router_v2 = VersionedAPIRouter(version="2.0")