import toml
from datetime import datetime
from easydict import EasyDict as edict
import os
import json
from sqlmodel import Session, select
from typing import Any, Dict, List
from .models import AppConfig, MonitoredDomain, TwitchConfig
from resonite_communities.utils.logger import get_logger


class ConfigManager:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.infrastructure_config = self._load_infrastructure_config()
        self.db_config = self._load_db_config() if db_session else {}
        self.config = self._build_legacy_config()
        self.logger = get_logger('ss')

    def _load_infrastructure_config(self):
        required_vars = [
            'PUBLIC_DOMAIN',
            'PRIVATE_DOMAIN',
            'DATABASE_URL',
            'CACHE_URL',
            'SECRET_KEY',
            'SECRET',
            'DISCORD_CLIENT_ID',
            'DISCORD_SECRET',
            'DISCORD_REDIRECT_URL',
            'SENTRY_DSN',
        ]
        config = {}
        missing_vars = []

        for var in required_vars:
            value = None
            file_path = os.getenv(f"{var}_FILE")

            if file_path and os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    value = f.read().strip()
            else:
                value = os.getenv(var)

            if value is None:
                missing_vars.append(var)
            else:
                config[var] = value

        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


        config['PUBLIC_DOMAIN'] = config['PUBLIC_DOMAIN'].split(',')
        config['PRIVATE_DOMAIN'] = config['PRIVATE_DOMAIN'].split(',')

        return config

    def _load_db_config(self):
        config = {}

        stmt = select(AppConfig)
        for session in self.db_session():
            app_config = session.execute(stmt).scalars().first()

            if app_config:
                config.update({
                    'DISCORD_BOT_TOKEN': app_config.discord_bot_token,
                    'AD_DISCORD_BOT_TOKEN': app_config.ad_discord_bot_token,
                    'REFRESH_INTERVAL': app_config.refresh_interval,
                    'CLOUDVAR_RESONITE_USER': app_config.cloudvar_resonite_user,
                    'CLOUDVAR_RESONITE_PASS': app_config.cloudvar_resonite_pass,
                    'CLOUDVAR_BASE_NAME': app_config.cloudvar_base_name,
                    'CLOUDVAR_GENERAL_NAME': app_config.cloudvar_general_name,
                    'FACET_URL': app_config.facet_url,
                })

            stmt = select(MonitoredDomain)
            domains = session.execute(stmt).scalars().all()
            config['MONITORED_DOMAINS'] = [
                {'url': domain.url, 'status': domain.status}
                for domain in domains
            ]

            stmt = select(TwitchConfig)
            twitch_config = session.execute(stmt).scalars().first()
            if twitch_config:
                config['Twitch'] = {
                    'client_id': twitch_config.client_id,
                    'secret': twitch_config.secret,
                    'game_id': twitch_config.game_id,
                    'account_name': twitch_config.account_name
                }

        return config

    def _build_legacy_config(self):
        config = self.infrastructure_config.copy()

        config.update(self.db_config)

        Config = edict(config)
        Config.clients = edict()

        return Config

    def load(self, model):
        for session in self.db_session():
            stmt = select(model)
            return session.execute(stmt).scalars().all()

    def update_app_config(self, **kwargs):
        for session in self.db_session():
            stmt = select(AppConfig)
            app_config = session.execute(stmt).scalars().first()

            if app_config:
                for key, value in kwargs.items():
                    if hasattr(app_config, key):
                        if key == "refresh_interval" and value == "":
                            value = 0
                        setattr(app_config, key, value)
            else:
                app_config = AppConfig(**kwargs)
                session.add(app_config)

            session.commit()
            session.refresh(app_config)

            self.db_config = self._load_db_config()
            self.config = self._build_legacy_config()

    def update_monitored_domain(self, domain_id: int, **kwargs):
        for session in self.db_session():
            stmt = select(MonitoredDomain).where(MonitoredDomain.id == domain_id)
            monitored_domain = session.execute(stmt).scalars().first()

            if monitored_domain:
                for key, value in kwargs.items():
                    if hasattr(monitored_domain, key):
                        setattr(monitored_domain, key, value)
                session.add(monitored_domain)
                session.commit()
                session.refresh(monitored_domain)

            self.db_config = self._load_db_config()
            self.config = self._build_legacy_config()

    def add_monitored_domain(self, url: str, status: str):
        for session in self.db_session():
            new_domain = MonitoredDomain(url=url, status=status)
            session.add(new_domain)
            session.commit()
            session.refresh(new_domain)

            self.db_config = self._load_db_config()
            self.config = self._build_legacy_config()

    def delete_monitored_domain(self, domain_id: int):
        for session in self.db_session():
            stmt = select(MonitoredDomain).where(MonitoredDomain.id == domain_id)
            domain_to_delete = session.execute(stmt).scalars().first()

            if domain_to_delete:
                session.delete(domain_to_delete)
                session.commit()

            self.db_config = self._load_db_config()
            self.config = self._build_legacy_config()

    def update_twitch_config(self, **kwargs):
        for session in self.db_session():
            stmt = select(TwitchConfig)
            twitch_config = session.execute(stmt).scalars().first()

            if twitch_config:
                for key, value in kwargs.items():
                    if hasattr(twitch_config, key):
                        setattr(twitch_config, key, value)
                session.add(twitch_config)
                session.commit()
                session.refresh(twitch_config)
            else:
                twitch_config = TwitchConfig(**kwargs)
                session.add(twitch_config)
                session.commit()
                session.refresh(twitch_config)

            self.db_config = self._load_db_config()
            self.config = self._build_legacy_config()
