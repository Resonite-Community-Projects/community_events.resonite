from fastapi import APIRouter
from fastapi_versionizer.versionizer import api_version

router = APIRouter()

@api_version(2, 1)
@router.get("/users/")
async def read_users():
    return [{"name": "Item 1"}, {"name": "Item 2"}]