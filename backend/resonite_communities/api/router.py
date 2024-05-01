from fastapi import APIRouter

from resonite_communities.api.routes import v1, v2

api_router = APIRouter()

api_router.include_router(v1.router)
api_router.include_router(v2.router)
