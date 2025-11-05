import argparse
import uvicorn
import multiprocessing

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

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




app.include_router(router_v1)
app.include_router(router_v2)

# TODO: This is duplicated endpoint with clients web routers admin configuration

from fastapi import Depends, HTTPException, Request
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.utils.config.models import MonitoredDomain
from resonite_communities.utils.db import get_current_async_session
import json

@app.post("/admin/update/configuration")
async def update_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        raise HTTPException(status_code=403, detail="Not authenticated or not a superuser.")

    session = await get_current_async_session()
    form_data = await request.form()
    config_manager = ConfigManager()

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
        await config_manager.update_app_config(session=session, **app_config_data)

    # Process MonitoredDomain
    existing_domains = await config_manager.load(MonitoredDomain, session=session)
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
            await config_manager.update_monitored_domain(session=session, domain_id=domain_key, **data)
        else: # New domain
            await config_manager.add_monitored_domain(session=session, url=data.get('url'), status=data.get('status'))

    # Delete removed domains
    domains_to_delete = existing_domain_ids - submitted_domain_ids
    for domain_id in domains_to_delete:
        await config_manager.delete_monitored_domain(session=session, domain_id=domain_id)

    # Process TwitchConfig
    twitch_config_data = {}
    for key, value in form_data.items():
        if key.startswith("twitch_config_"):
            twitch_config_data[key.replace("twitch_config_", "")] = value
    if twitch_config_data:
        await config_manager.update_twitch_config(session=session, **twitch_config_data)

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
            "workers": config_manager.infrastructure_config.API_WORKERS,
            "worker_class": "uvicorn.workers.UvicornWorker",
        }
        StandaloneApplication(app, options).run()
