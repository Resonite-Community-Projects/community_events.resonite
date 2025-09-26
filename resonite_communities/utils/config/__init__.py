import toml
from datetime import datetime
from easydict import EasyDict as edict
import os
import json
import multiprocessing
from sqlmodel import select
from typing import Any, Dict, List
from .models import AppConfig, MonitoredDomain, TwitchConfig
from resonite_communities.utils.logger import get_logger

class ConfigManager:
    def __init__(self):
        self.infrastructure_config = self._load_infrastructure_config()
        self.app_config = self._load_db_config
        self.config = self._build_legacy_config
        self.logger = get_logger(__name__)

    async def _get_session(self):
        # Import inside the method to avoid circular imports
        from resonite_communities.utils.db import get_current_async_session
        return await get_current_async_session()


    def _load_infrastructure_config(self):
        optional_vars = [
            'PRIVATE_DOMAIN',
            'DB_POOL_SIZE',
            'DB_MAX_OVERFLOW',
            'DB_POOL_TIMEOUT',
            'DB_POOL_RECYCLE',
            'DB_POOL_PRE_PING',
            'WEB_WORKERS',
            'API_WORKERS',
        ]
        required_vars = [
            'PUBLIC_DOMAIN',
            'DATABASE_URL',
            'CACHE_URL',
            'SECRET_KEY',
            'SECRET',
            'DISCORD_CLIENT_ID',
            'DISCORD_SECRET',
            'DISCORD_REDIRECT_URL',
            'SENTRY_DSN',
        ]

        defaults = {
            'DB_POOL_SIZE': 6,
            'DB_MAX_OVERFLOW': 8,
            'DB_POOL_TIMEOUT': 30,
            'DB_POOL_RECYCLE': 1800,
            'DB_POOL_PRE_PING': True,
            'WEB_WORKERS': 3,
            'API_WORKERS': 3,
        }

        config = {}
        missing_vars = []
        all_vars = required_vars + optional_vars

        for var in all_vars:
            value = None
            file_path = os.getenv(f"{var}_FILE")

            if file_path and os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    value = f.read().strip()
            else:
                value = os.getenv(var)

            if var not in optional_vars and value is None:
                missing_vars.append(var)
            elif value is not None:
                config[var] = value

        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value

        config['PUBLIC_DOMAIN'] = config['PUBLIC_DOMAIN'].split(',')
        config['PRIVATE_DOMAIN'] = config['PRIVATE_DOMAIN'].split(',') if config.get('PRIVATE_DOMAIN') else []

        return edict(config)

    async def _load_db_config(self):
        config = self.infrastructure_config.copy()
        session = await self._get_session()

        stmt = select(AppConfig)
        result = await session.execute(stmt)
        app_config = result.scalars().first()

        config.update({
            'INITIATED': app_config.initiated if app_config else False,
            'DISCORD_BOT_TOKEN': app_config.discord_bot_token if app_config else '',
            'AD_DISCORD_BOT_TOKEN': app_config.ad_discord_bot_token if app_config else '',
            'REFRESH_INTERVAL': app_config.refresh_interval if app_config else '',
            'CLOUDVAR_RESONITE_USER': app_config.cloudvar_resonite_user if app_config else '',
            'CLOUDVAR_RESONITE_PASS': app_config.cloudvar_resonite_pass if app_config else '',
            'CLOUDVAR_BASE_NAME': app_config.cloudvar_base_name if app_config else '',
            'CLOUDVAR_GENERAL_NAME': app_config.cloudvar_general_name if app_config else '',
            'NORMAL_USER_LOGIN': app_config.normal_user_login if app_config else False,
            'FACET_URL': app_config.facet_url if app_config else '',
            'TITLE_TEXT': app_config.title_text if app_config else '',
            'HERO_COLOR': app_config.hero_color if app_config else '',
            'INFO_TEXT': app_config.info_text if app_config else '',
            'FOOTER_TEXT': app_config.footer_text if app_config else '',
        })

        stmt = select(MonitoredDomain)
        result = await session.execute(stmt)
        domains = result.scalars().all()
        config['MONITORED_DOMAINS'] = [
            {'url': domain.url, 'status': domain.status}
            for domain in domains
        ]

        stmt = select(TwitchConfig)
        result = await session.execute(stmt)
        twitch_config = result.scalars().first()
        config['Twitch'] = {
            'client_id': twitch_config.client_id if twitch_config else '',
            'secret': twitch_config.secret if twitch_config else '',
            'game_id': twitch_config.game_id if twitch_config else '',
            'account_name': twitch_config.account_name if twitch_config else ''
        }

        return edict(config)

    async def _build_legacy_config(self):
        config = self.infrastructure_config.copy()

        db_config = await self._load_db_config()
        config.update(db_config)

        Config = edict(config)
        Config.clients = edict()

        return Config

    async def load(self, model):
        session = await self._get_session()
        stmt = select(model)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_app_config(self, **kwargs):
        session = await self._get_session()
        stmt = select(AppConfig)
        result = await session.execute(stmt)
        app_config = result.scalars().first()

        if app_config:
            for key, value in kwargs.items():
                if hasattr(app_config, key):
                    if key == "refresh_interval":
                        if value == "":
                            value = 0
                        else:
                            value = int(value)
                    setattr(app_config, key, value)
        else:
            app_config = AppConfig(**kwargs)
            session.add(app_config)

        await session.commit()
        await session.refresh(app_config)

    async def update_monitored_domain(self, domain_id: int, **kwargs):
        session = await self._get_session()
        stmt = select(MonitoredDomain).where(MonitoredDomain.id == domain_id)
        result = await session.execute(stmt)
        monitored_domain = result.scalars().first()

        if monitored_domain:
            for key, value in kwargs.items():
                if hasattr(monitored_domain, key):
                    setattr(monitored_domain, key, value)
            session.add(monitored_domain)
            await session.commit()
            await session.refresh(monitored_domain)

    async def add_monitored_domain(self, url: str, status: str):
        session = await self._get_session()
        new_domain = MonitoredDomain(url=url, status=status)
        session.add(new_domain)
        await session.commit()
        await session.refresh(new_domain)

    async def delete_monitored_domain(self, domain_id: int):
        session = await self._get_session()
        stmt = select(MonitoredDomain).where(MonitoredDomain.id == domain_id)
        result = await session.execute(stmt)
        domain_to_delete = result.scalars().first()

        if domain_to_delete:
            await session.delete(domain_to_delete)
            await session.commit()

    async def update_twitch_config(self, **kwargs):
        session = await self._get_session()
        stmt = select(TwitchConfig)
        result = await session.execute(stmt)
        twitch_config = result.scalars().first()

        if twitch_config:
            for key, value in kwargs.items():
                if hasattr(twitch_config, key):
                    setattr(twitch_config, key, value)
            session.add(twitch_config)
            await session.commit()
            await session.refresh(twitch_config)
        else:
            twitch_config = TwitchConfig(**kwargs)
            session.add(twitch_config)
            await session.commit()
            await session.refresh(twitch_config)
