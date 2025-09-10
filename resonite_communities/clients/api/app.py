import argparse
import uvicorn
import multiprocessing

from fastapi import FastAPI

from resonite_communities.clients import StandaloneApplication

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session

from resonite_communities.clients.middleware.metrics import MetricsMiddleware
from resonite_communities.clients.utils.geoip import get_geoip_db_path

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from redis import asyncio as aioredis

Config = ConfigManager(get_session).config()

# @asynccontextmanager
# async def lifespan(_: FastAPI) -> AsyncIterator[None]:
#     redis = aioredis.from_url(Config.CACHE_URL)
#     FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
#     yield

#app = FastAPI(lifespan=lifespan)
app = FastAPI()

app.add_middleware(MetricsMiddleware, db_path=get_geoip_db_path())

import resonite_communities.clients.api.routes.v1
import resonite_communities.clients.api.routes.v2

from resonite_communities.clients.api.routes.routers import router_v1
from resonite_communities.clients.api.routes.routers import router_v2




app.include_router(router_v1)
app.include_router(router_v2)

# TODO: This is duplicated endpoint with clients web routers admin configuration

from fastapi import Depends, HTTPException, Request
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.utils.config.models import MonitoredDomain
import json

@app.post("/admin/update/configuration")
async def update_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(status_code=403, detail="Not authenticated or not a superuser.")

    form_data = await request.form()
    config_manager = ConfigManager(get_session)

    # Process AppConfig
    app_config_data = {}
    for key, value in form_data.items():
        if key.startswith("app_config_"):
            field_name = key.replace("app_config_", "")
            if field_name in ["public_domain", "private_domain"]:
                app_config_data[field_name] = json.dumps([item.strip() for item in value.split(',')])
            else:
                app_config_data[field_name] = value
    if app_config_data:
        config_manager.update_app_config(**app_config_data)

    # Process MonitoredDomain
    existing_domains = config_manager.load(MonitoredDomain)
    existing_domain_ids = {domain.id for domain in existing_domains}
    submitted_domain_ids = set()
    monitored_domains_data = {}

    for key, value in form_data.items():
        if key.startswith("monitored_config_"):
            # Expecting monitored_config_{id}_field or monitored_config_new-{index}_field
            parts = key.split('_')
            if parts[2].startswith("new-"): # Expecting new-0, new-1
                domain_key = parts[2]
            else: # Expecting 1, 2, 3 (existing IDs)
                domain_key = int(parts[2])
                submitted_domain_ids.add(domain_key)

            field_name = "_".join(parts[3:])
            if domain_key not in monitored_domains_data:
                monitored_domains_data[domain_key] = {}
            monitored_domains_data[domain_key][field_name] = value

    # Update existing domains and add new ones
    for domain_key, data in monitored_domains_data.items():
        if isinstance(domain_key, int): # Existing domain
            config_manager.update_monitored_domain(domain_key, **data)
        else: # New domain
            config_manager.add_monitored_domain(url=data.get('url'), status=data.get('status'))

    # Delete removed domains
    domains_to_delete = existing_domain_ids - submitted_domain_ids
    for domain_id in domains_to_delete:
        config_manager.delete_monitored_domain(domain_id)

    # Process TwitchConfig
    twitch_config_data = {}
    for key, value in form_data.items():
        if key.startswith("twitch_config_"):
            twitch_config_data[key.replace("twitch_config_", "")] = value
    if twitch_config_data:
        config_manager.update_twitch_config(**twitch_config_data)

    return {"message": "Configuration updated successfully"}

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
            "workers": (multiprocessing.cpu_count() * 2) + 1,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        StandaloneApplication(app, options).run()
