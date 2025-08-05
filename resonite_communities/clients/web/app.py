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
from resonite_communities.clients.utils.geoip import get_geoip_db_path

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session

Config = ConfigManager(get_session).config()

app = FastAPI()
app.secret = Config.SECRET

app.mount(
    "/static",
    StaticFiles(directory="resonite_communities/clients/web/static"),
    name="static"
)

app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())

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
        Config.SECRET,
        redirect_url=Config.DISCORD_REDIRECT_URL
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
            "workers": (multiprocessing.cpu_count() * 2) + 1,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        StandaloneApplication(app, options).run()