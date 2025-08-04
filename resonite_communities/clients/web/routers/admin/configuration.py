import json
from copy import deepcopy
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy import case, and_
from sqlalchemy.orm import Session

from resonite_communities.clients.web.utils.templates import templates
from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.web.routers.utils import logo_base64
from resonite_communities.models.community import Community, CommunityPlatform
from resonite_communities.models.signal import Event
from resonite_communities.auth.db import User

from resonite_communities.utils.config import ConfigManager
from resonite_communities.auth.db import get_session
from resonite_communities.utils.logger import get_logger

Config = ConfigManager(get_session).config

router = APIRouter()

@router.get("/admin/configuration")
async def get_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):

    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    from sqlalchemy import select, create_engine
    from sqlmodel import Session

    engine = create_engine(Config.DATABASE_URL, echo=False)

    from sqlalchemy.orm import joinedload
    from resonite_communities.auth.db import OAuthAccount
    from resonite_communities.utils.config.models import AppConfig, MonitoredDomain, TwitchConfig

    def load(object):
        with Session(engine) as session:
            instances = []
            query = select(object)

            rows = session.exec(query).unique().all()
            for row in rows:
                instances.append(row[0])
            return instances

    app_config_objects = load(AppConfig)
    app_config = []
    for config in app_config_objects:
        app_config.append(config)
    monitored_config_objects = load(MonitoredDomain)
    monitored_config = [
        {"id": domain.id, "url": domain.url, "status": domain.status}
        for domain in monitored_config_objects
    ]
    twitch_config = load(TwitchConfig)

    try:
        api_url = Config.PUBLIC_DOMAIN[0]
    except (KeyError, IndexError):
        api_url = None

    if api_url and api_url.endswith(".local"):
        api_url = f"http://{api_url}"
    else:
        api_url = f"https://{api_url}"

    return templates.TemplateResponse("admin/configuration.html", {
        "userlogo" : logo_base64,
        "user" : deepcopy(user_auth),
        "api_url": Config.PUBLIC_DOMAIN,
        "app_config": app_config,
        "monitored_config": monitored_config,
        "twitch_config": twitch_config,
        "request": request,
    })

@router.post("/admin/update/configuration")
async def update_configuration(request: Request, user_auth: UserAuthModel = Depends(get_user_auth)):
    if not user_auth or not user_auth.is_superuser:
        return RedirectResponse(url="/")

    form_data = await request.form()
    config_manager = ConfigManager(get_session)

    # Process AppConfig
    app_config_data = {}
    for key, value in form_data.items():
        if key.startswith("app_config_"):
            app_config_data[key.replace("app_config_", "")] = value
    if app_config_data:
        config_manager.update_app_config(**app_config_data)

    from sqlalchemy import select, create_engine
    from sqlmodel import Session

    engine = create_engine(Config.DATABASE_URL, echo=False)

    def load(object):
        with Session(engine) as session:
            instances = []
            query = select(object)

            rows = session.exec(query).unique().all()
            for row in rows:
                instances.append(row[0])
            return instances


    # Process Monitored Domains (additions, updates, deletions)
    from resonite_communities.utils.config.models import MonitoredDomain
    existing_monitored_domains = load(MonitoredDomain)
    existing_domain_ids = {domain.id for domain in existing_monitored_domains}

    submitted_monitored_domains = {}
    for key, value in form_data.items():
        if key.startswith("monitored_config_"):
            parts = key.split('_')
            # Expected format: monitored_config_{id}_url or monitored_config_{id}_status
            # parts[2] is the ID ('new-X' or an integer)
            # parts[3:] is the field name ('url', 'status', etc)
            domain_id_str = parts[2]
            field_name = "_".join(parts[3:])

            if domain_id_str not in submitted_monitored_domains:
                submitted_monitored_domains[domain_id_str] = {}
            submitted_monitored_domains[domain_id_str][field_name] = value

    # Process updates and additions
    for domain_id_str, data in submitted_monitored_domains.items():
        if domain_id_str.startswith("new-"):
            # New domain
            config_manager.add_monitored_domain(url=data.get('url'), status=data.get('status'))
        else:
            # Existing domain
            domain_id = int(domain_id_str)
            if domain_id in existing_domain_ids:
                config_manager.update_monitored_domain(domain_id, **data)

    # Process deletions
    submitted_ids = {int(d_id) for d_id in submitted_monitored_domains.keys() if not d_id.startswith("new-")}
    for existing_id in existing_domain_ids:
        if existing_id not in submitted_ids:
            config_manager.delete_monitored_domain(existing_id)

    # Process TwitchConfig
    twitch_config_data = {}
    for key, value in form_data.items():
        if key.startswith("twitch_config_"):
            twitch_config_data[key.replace("twitch_config_", "")] = value
    if twitch_config_data:
        config_manager.update_twitch_config(**twitch_config_data)

    return JSONResponse(content={"message": "Configuration updated successfully"})
