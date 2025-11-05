import argparse
import multiprocessing
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from resonite_communities.auth.users import fastapi_users, auth_backend
from resonite_communities.clients.web.auth import discord_oauth
from resonite_communities.clients import StandaloneApplication
from resonite_communities.clients.web.routers import (
    main,
    login,
    logout,
)
from resonite_communities.clients.web.routers.admin import metrics, events, communities, users, configuration
from resonite_communities.clients.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.middleware.rate_limit import RateLimitMiddleware
from resonite_communities.clients.utils.geoip import get_geoip_db_path

from resonite_communities.utils.config import ConfigManager

# Ensure models are loaded for SQLAlchemy relationship resolution
from resonite_communities.models.signal import Event, Stream
from resonite_communities.models.community import Community

config_manager = ConfigManager()

app = FastAPI()
app.secret = config_manager.infrastructure_config.SECRET

app.mount(
    "/static",
    StaticFiles(directory="resonite_communities/clients/web/static"),
    name="static"
)

from resonite_communities.utils.db import get_async_session, async_request_session
from starlette.middleware.base import BaseHTTPMiddleware


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        async with async_request_session():
            response = await call_next(request)
        return response


app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())
app.add_middleware(
    RateLimitMiddleware,
    max_concurrent_requests=config_manager.infrastructure_config.MAX_CONCURRENT_REQUESTS
)
app.add_middleware(DatabaseSessionMiddleware)

app.include_router(logout.router)
app.include_router(login.router)
app.include_router(main.router)
app.include_router(metrics.router)
app.include_router(events.router)
app.include_router(users.router)
app.include_router(communities.router)
app.include_router(configuration.router)

app.include_router(
    fastapi_users.get_oauth_router(
        discord_oauth,
        auth_backend,
        config_manager.infrastructure_config.SECRET,
        redirect_url=config_manager.infrastructure_config.DISCORD_REDIRECT_URL
    ),
    prefix="/auth/discord",
    tags=["auth"],
)

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    # TODO: Fixme!
    #if request.url.path.startswith("/static"):
    #    return await app.default_exception_handler(exc)
    return RedirectResponse("/")

@app.exception_handler(401)
async def custom_401_handler(_, __):
    return RedirectResponse("/")

def run():
    parser = argparse.ArgumentParser(description="Run the server")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0:8001",
        help="Bind address (default: 0.0.0.0:8001)",
        metavar="<IP:PORT>",
    )
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Enable autoreload with uvicorn"
    )

    args = parser.parse_args()

    if args.reload:
        host, port = args.address.split(":")
        uvicorn.run(
            "resonite_communities.clients.web.app:app",
            host=host,
            port=int(port),
            reload=True,
        )
    else:
        options = {
            "bind": args.address,
            "workers": config_manager.infrastructure_config.WEB_WORKERS,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        StandaloneApplication(app, options).run()
