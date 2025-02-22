import argparse
import multiprocessing

from fastapi import FastAPI

from resonite_communities.auth.users import fastapi_users, auth_backend
from resonite_communities.clients.web.auth import discord_oauth
from resonite_communities.clients import StandaloneApplication
from resonite_communities.utils import Config
from resonite_communities.clients.web.routers import (
    main,
    login,
    logout,
    metrics,
)
from resonite_communities.clients.web.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.web.utils.geoip import get_geoip_db_path

app = FastAPI()
app.secret = Config.SECRET

app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())

app.include_router(logout.router)
app.include_router(login.router)
app.include_router(main.router)

app.include_router(metrics.router)

app.include_router(
    fastapi_users.get_oauth_router(
        discord_oauth,
        auth_backend,
        Config.SECRET,
        redirect_url=Config.Discord.client.redirect_uri
    ),
    prefix="/auth/discord",
    tags=["auth"],
)

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

    args = parser.parse_args()

    options = {
        "bind": args.address,
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
    }
    StandaloneApplication(app, options).run()
