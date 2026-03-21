from sqlalchemy import select
from fastapi import Depends, HTTPException

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.api.utils.auth import get_user_auth_from_header_or_cookie
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager


config_manager = ConfigManager()

logger = get_logger(__name__)

async def load(model_class, session):
    instances = []
    query = select(model_class).execution_options(populate_existing=True)
    result = await session.execute(query)
    rows = result.unique().all()
    for row in rows:
        instances.append(row[0])
    return instances


def require_moderator_access(user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)) -> UserAuthModel:
    if not user_auth or not (user_auth.is_superuser or user_auth.is_moderator):
        raise HTTPException(
            status_code=403,
            detail="Moderator or administrator access required",
        )
    return user_auth

def require_administrator_access(user_auth: UserAuthModel = Depends(get_user_auth_from_header_or_cookie)) -> UserAuthModel:
    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )
    return user_auth

