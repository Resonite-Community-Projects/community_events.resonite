import json
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from resonite_communities.clients.utils.auth import UserAuthModel, get_user_auth
from resonite_communities.clients.api.routes.routers import router_v2
from resonite_communities.utils.db import get_current_async_session
from resonite_communities.utils.logger import get_logger
from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.config.models import MonitoredDomain

from resonite_communities.clients.api.routes.v2.admin import require_administrator_access
from resonite_communities.clients.api.routes.v2.admin import load

config_manager = ConfigManager()

logger = get_logger(__name__)

class ConfigurationResponse(BaseModel):
    app_config: dict
    monitored_config: List[dict]
    twitch_config: List[dict]

class MonitoredDomainUpdate(BaseModel):
    id: Optional[int] = None
    url: str
    status: str

class ConfigurationUpdateRequest(BaseModel):
    # AppConfig fields
    app_config_normal_user_login: Optional[str] = None
    app_config_hero_color: Optional[str] = None
    app_config_title_text: Optional[str] = None
    app_config_info_text: Optional[str] = None
    app_config_footer_text: Optional[str] = None
    app_config_discord_bot_token: Optional[str] = None
    app_config_ad_discord_bot_token: Optional[str] = None
    app_config_refresh_interval: Optional[int] = None
    app_config_cloudvar_resonite_user: Optional[str] = None
    app_config_cloudvar_resonite_pass: Optional[str] = None
    app_config_cloudvar_base_name: Optional[str] = None
    app_config_cloudvar_general_name: Optional[str] = None
    app_config_facet_url: Optional[str] = None

    # TwitchConfig fields
    twitch_config_client_id: Optional[str] = None
    twitch_config_secret: Optional[str] = None
    twitch_config_game_id: Optional[str] = None
    twitch_config_account_name: Optional[str] = None

    # MonitoredDomains - format: {domain_id: {url, status}}
    monitored_domains: Optional[dict] = None

@router_v2.post("/admin/configuration")
async def update_admin_configuration(
    data: dict,
    user_auth: UserAuthModel = Depends(require_administrator_access)
):
    try:
        session = await get_current_async_session()

        # Process AppConfig
        app_config_data = {}
        for key, value in data.items():
            if key == 'app_config_normal_user_login':
                value = True if value == 'ENABLED' else False
            if key.startswith("app_config_"):
                app_config_data[key.replace("app_config_", "")] = value

        if app_config_data:
            await config_manager.update_app_config(session=session, **app_config_data)

        # Process Monitored Domains (additions, updates, deletions)
        existing_monitored_domains = await load(MonitoredDomain, session)
        existing_domain_ids = {domain.id for domain in existing_monitored_domains}

        submitted_monitored_domains = {}
        for key, value in data.items():
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
        for domain_id_str, domain_data in submitted_monitored_domains.items():
            if domain_id_str.startswith("new-"):
                # New domain
                await config_manager.add_monitored_domain(
                    session=session,
                    url=domain_data.get('url'),
                    status=domain_data.get('status')
                )
            else:
                # Existing domain
                domain_id = int(domain_id_str)
                if domain_id in existing_domain_ids:
                    await config_manager.update_monitored_domain(session=session, domain_id=domain_id, **domain_data)

        # Process deletions
        submitted_ids = {
            int(d_id) for d_id in submitted_monitored_domains.keys()
            if not d_id.startswith("new-")
        }
        for existing_id in existing_domain_ids:
            if existing_id not in submitted_ids:
                await config_manager.delete_monitored_domain(session=session, domain_id=existing_id)

        # Process TwitchConfig
        twitch_config_data = {}
        for key, value in data.items():
            if key.startswith("twitch_config_"):
                twitch_config_data[key.replace("twitch_config_", "")] = value

        if twitch_config_data:
            await config_manager.update_twitch_config(session=session, **twitch_config_data)

    except SQLAlchemyError as e:
        logger.error(f"Database error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Configuration update failed")

    logger.info(f"System configuration updated successfully")
    return {"message": "Configuration updated successfully"}

@router_v2.post("/admin/update/configuration")
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
