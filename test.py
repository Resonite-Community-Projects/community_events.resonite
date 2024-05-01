from fastapi import APIRouter, Depends, FastAPI
from fastapi_versionizer import api_version, Versionizer

class VersionedAPIRouter(APIRouter):

    def __init__(self, version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.major, self.minor = version.split('.')

    def add_api_route(self, *args, **kwargs):
        super().add_api_route(*args, **kwargs)
        for route in self.routes:
            try:
                route.endpoint._api_version = (self.major, self.minor)
            except AttributeError:
                # Support bound methods
                route.endpoint.__func__._api_version = (self.major, self.minor)


router_v1 = VersionedAPIRouter(version="1.0")

@router_v1.get("/items/")
async def read_items():
    return "name:Item 1,name: Item 2"


router_v2 = VersionedAPIRouter(version="2.0")

@router_v2.get("/items/")
async def read_items():
    return [{"name": "Item 1"}, {"name": "Item 2"}]


app = FastAPI()

app.include_router(router_v1)
app.include_router(router_v2)

versions = Versionizer(
    app=app,
    prefix_format='/v{major}',
    semantic_version_format='{major}',
    sort_routes=True,
).versionize()