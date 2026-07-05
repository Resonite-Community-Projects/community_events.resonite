from fastapi import APIRouter

class VersionedAPIRouter(APIRouter):

    def __init__(self, version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.major = int(version.split('.')[0])
        self.minor = int(version.split('.')[1])

    def add_api_route(self, *args, **kwargs):
        super().add_api_route(*args, **kwargs)
        for route in self.routes:

            # This try/catch is here to see if having a version 2.0 and 2.1 is supported, need to look deeper
            # It's accepted by the code but their is no much difference on the swagger side, is it really supported?
            try:
                route.endpoint._api_version
                continue
            except Exception:
                pass

            try:
                route.endpoint._api_version = (self.major, self.minor)
            except AttributeError:
                # Support bound methods
                route.endpoint.__func__._api_version = (self.major, self.minor)
