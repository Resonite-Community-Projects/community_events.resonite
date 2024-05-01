from fastapi import APIRouter, Depends, FastAPI
from fastapi_versionizer import api_version, Versionizer

from resonite_communities.api.router import api_router

app = FastAPI()

app.include_router(api_router)


versions = Versionizer(
    app=app,
    prefix_format='/v{major}',
    semantic_version_format='{major}',
    sort_routes=True,
).versionize()


print('----')
for route in app.routes:
    print(route)
