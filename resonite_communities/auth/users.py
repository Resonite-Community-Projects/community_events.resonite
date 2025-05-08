# fastapi_users, auth_backend
import uuid
from typing import Optional

from fastapi import Depends, Request, Response
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from resonite_communities.auth.db import User, get_user_db
from resonite_communities.utils import get_logger, Config, is_local_env

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = Config.SECRET
    verification_token_secret = Config.SECRET

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)

    # FIXME: This code should be removed when the web client is deleted, see it's own README.md
    async def oauth_callback(
        self,
        oauth_name,
        access_token,
        account_id,
        account_email,
        expires_at = None,
        refresh_token = None,
        request = None,
        *,
        associate_by_email = False,
        is_verified_by_default = False
    ):
        from fastapi_users.exceptions import UserAlreadyExists
        from fastapi import HTTPException
        try:
            user = await super().oauth_callback(
                oauth_name,
                access_token,
                account_id,
                account_email,
                expires_at,
                refresh_token,
                request,
                associate_by_email=associate_by_email,
                is_verified_by_default=is_verified_by_default
            )
        except UserAlreadyExists:
            # NOTE: If the oauth_account have been clean but not the user link to it this will cause this error.
            raise HTTPException(
                status_code=400,
                detail="This email address is already used in another account. Please contact brodokk (See https://brodokk.space/).",
            )

        self.logger.info(f"User {user.id} has logged in.")

        from fastapi_users.exceptions import FastAPIUsersException

        class OAuth2Error(FastAPIUsersException):
            pass

        access_token = None
        oauth_account = None
        for user_oauth_account in user.oauth_accounts:
            if user_oauth_account.oauth_name == "discord":
                oauth_account = user_oauth_account
                access_token = user_oauth_account.access_token
                break

        if not access_token:
            raise OAuth2Error("Failed to retrieve access token")

        # TODO: Need to think harder about that the rate limit on this is really really bad

        from resonite_communities.clients.web.utils.discord import get_current_user, get_user_guilds, get_user_roles_in_guild_safe

        user_data = get_current_user(access_token)
        guilds = get_user_guilds(access_token)

        from resonite_communities.utils import Config
        from resonite_communities.models.community import Community

        communities = {community.external_id:community.id for community in Community().find()}

        private_events_access_communities = {'guilds': [], 'retry_after': 0}
        for guild in guilds:
            if guild['name'] in private_events_access_communities['guilds']:
                continue
            for configured_guild in Config.SIGNALS.DiscordEventsCollector:
                if str(configured_guild['external_id']) == str(guild['id']):
                    private_role_id = configured_guild.get(
                        'config', {}).get('private_role_id')
                    if private_role_id:
                        user_roles, retry_after = get_user_roles_in_guild_safe(
                            access_token, guild['id']
                        )
                        if retry_after > private_events_access_communities['retry_after']:
                            private_events_access_communities['retry_after'] = retry_after
                        for user_role in user_roles:
                            if (
                                str(user_role) == str(configured_guild.get('config', {}).get('private_role_id')) and
                                guild['id'] in communities
                            ):
                                private_events_access_communities['guilds'].append(
                                    str(communities[guild['id']])
                                )

        from resonite_communities.auth.db import (
            DiscordAccount,
            OAuthAccount,
            get_async_session,
        )
        import contextlib

        get_async_session_context = contextlib.asynccontextmanager(get_async_session)

        async with get_async_session_context() as session:

            oauth_account_db = await session.get(OAuthAccount, oauth_account.id)
            discord_account_db = await session.get(DiscordAccount, oauth_account_db.discord_account_id)

            if oauth_account_db.discord_account_id and discord_account_db:
                    discord_account_db.name = user_data["username"]
                    discord_account_db.avatar_url = user_data["avatar_url"]
                    discord_account_db.user_communities = private_events_access_communities["guilds"]
                    discord_account_db.discord_update_retry_after = private_events_access_communities["retry_after"]
                    session.add(discord_account_db)
                    await session.commit()
            else:
                discord_account = DiscordAccount(
                    name=user_data["username"],
                    avatar_url=user_data["avatar_url"],
                    user_communities=private_events_access_communities['guilds'],
                    discord_update_retry_after = private_events_access_communities["retry_after"],
                )
                session.add(discord_account)

                await session.commit()

                oauth_account_db.discord_account_id = discord_account.id

                await session.commit()

        return user


    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        self.logger.info(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None) -> None:
        self.logger.info(
            f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None) -> None:
        self.logger.info(
            f"User {user.id} has requested to verify their email. Verification token: {token}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)) -> UserManager:
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

from starlette.responses import RedirectResponse
from fastapi_users.authentication.transport.cookie import CookieTransport

class MyCookieTransport(CookieTransport):

    async def get_login_response(self, token: str) -> Response:
        response = RedirectResponse(url="/")
        return self._set_login_cookie(response, token)

    async def get_logout_response(self) -> Response:
        response = RedirectResponse(url="/")
        return self._set_logout_cookie(response)

cookie_secure = True
if is_local_env:
    cookie_secure = False

cookie_transport = MyCookieTransport(cookie_secure=cookie_secure)


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(secret=Config.SECRET, lifetime_seconds=3600)

from resonite_communities.auth.db import AccessToken, get_access_token_db
from fastapi_users.authentication.strategy.db import AccessTokenDatabase, DatabaseStrategy

def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_database_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
optional_current_active_user = fastapi_users.current_user(active=True, optional=True)
