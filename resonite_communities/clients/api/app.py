import argparse
import uvicorn
import multiprocessing

from fastapi import FastAPI, Request, APIRouter
from fastapi_versionizer import Versionizer
from starlette.middleware.base import BaseHTTPMiddleware
import sentry_sdk

from resonite_communities.clients import StandaloneApplication

from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.db import async_request_session

config_manager = ConfigManager()

from resonite_communities.clients.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.middleware.rate_limit import RateLimitMiddleware
from resonite_communities.clients.utils.geoip import get_geoip_db_path

class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        async with async_request_session():
            response = await call_next(request)
        return response

if config_manager.infrastructure_config.SENTRY_DSN:

    sentry_sdk.init(
        dsn=config_manager.infrastructure_config.SENTRY_DSN,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Enable sending logs to Sentry
        enable_logs=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profile_session_sample_rate to 1.0 to profile 100%
        # of profile sessions.
        profile_session_sample_rate=1.0,
        # Set profile_lifecycle to "trace" to automatically
        # run the profiler on when there is an active transaction
        profile_lifecycle="trace",
    )

app = FastAPI()

app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())
app.add_middleware(DatabaseSessionMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    max_concurrent_requests=config_manager.infrastructure_config.MAX_CONCURRENT_REQUESTS
)

import resonite_communities.clients.api.routes.v1
import resonite_communities.clients.api.routes.v2

from resonite_communities.clients.api.routes.routers import router_v1
from resonite_communities.clients.api.routes.routers import router_v2


api_router = APIRouter()
api_router.include_router(router_v1)
api_router.include_router(router_v2)

app.include_router(api_router)

Versionizer(
    app=app,
    prefix_format='/v{major}',
    semantic_version_format='{major}',
    sort_routes=True,
).versionize()

# TODO: This is duplicated endpoint with clients web routers admin configuration

from fastapi import Depends, HTTPException, Request
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.utils.config.models import MonitoredDomain
from resonite_communities.utils.db import get_current_async_session
import json

def run():
    parser = argparse.ArgumentParser(description="Run the server")
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        default="0.0.0.0:8000",
        help="Bind address (default: 0.0.0.0:8000)",
        metavar="<IP:PORT>"
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
            "resonite_communities.clients.api.app:app",
            host=host,
            port=int(port),
            reload=True,
        )
    else:
        options = {
            "bind": args.address,
            "workers": config_manager.infrastructure_config.API_WORKERS,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        StandaloneApplication(app, options).run()
