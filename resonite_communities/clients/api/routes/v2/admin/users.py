from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from resonite_communities.clients.utils.auth import UserAuthModel
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.auth.db import User, OAuthAccount
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager

from resonite_communities.clients.api.routes.v2.admin import require_administrator_access

config_manager = ConfigManager()

logger = get_logger(__name__)

class UserUpdateStatusRequest(BaseModel):
    id: str
    is_superuser: bool
    is_moderator: bool


@router_v2.post("/admin/users/update_status")
async def update_user_status(data: UserUpdateStatusRequest, user_auth: UserAuthModel = Depends(require_administrator_access)):
    try:
        result = await User.update(
            filters=(User.id == data.id),
            is_superuser=data.is_superuser,
            is_moderator=data.is_moderator
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating user {data.id} permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not result:
        logger.warning(f"User {data.id} not found for status update")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"User {data.id} permissions updated - superuser: {data.is_superuser}, moderator: {data.is_moderator}")
    return {"id": data.id, "message": "User permissions updated successfully"}

@router_v2.get("/admin/users")
async def get_admin_users(
    user_auth: UserAuthModel = Depends(require_administrator_access)
):
    session = await get_current_async_session()

    # Query users with joinedload for relationships
    try:
        query = select(User).options(
            joinedload(User.oauth_accounts).joinedload(OAuthAccount.discord_account)
        ).execution_options(populate_existing=True)

        result = await session.execute(query)
        rows = result.unique().all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching admin users: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    users = []
    for row in rows:
        user = row[0]

        # Build user data with relationships
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "is_moderator": user.is_moderator,
            "is_protected": user.is_protected,
            "oauth_accounts": []
        }

        # Add OAuth accounts with Discord data
        for oauth_account in user.oauth_accounts:
            oauth_data = {
                "id": str(oauth_account.id),
                "oauth_name": oauth_account.oauth_name,
                "access_token": oauth_account.access_token,
                "expires_at": oauth_account.expires_at,
                "refresh_token": oauth_account.refresh_token,
                "account_id": oauth_account.account_id,
                "account_email": oauth_account.account_email
            }

            # Add Discord account data if available
            if oauth_account.discord_account:
                discord = oauth_account.discord_account
                oauth_data["discord_account"] = {
                    "id": str(discord.id),
                    "name": discord.name,
                    "avatar_url": discord.avatar_url,
                    "user_communities": discord.user_communities,
                    "discord_update_retry_after": discord.discord_update_retry_after
                }
            else:
                oauth_data["discord_account"] = None

            user_data["oauth_accounts"].append(oauth_data)

        users.append(user_data)

    return users
