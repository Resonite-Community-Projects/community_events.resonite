import httpx
from typing import Dict, Any, Optional
from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.logger import get_logger
from resonite_communities.clients.utils.auth import UserAuthModel
import json

config_manager = ConfigManager()
logger = get_logger('WebAPIClient')

class APIClient:

    def __init__(self):
        try:
            self.api_url = config_manager.infrastructure_config.PUBLIC_DOMAIN[0]
        except (KeyError, IndexError):
            self.api_url = None

        if self.api_url and self.api_url.endswith(".local"):
            self.api_url = f"http://{self.api_url}"
        else:
            self.api_url = f"https://{self.api_url}"

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, user_auth: Optional[UserAuthModel] = None):
        headers = {}
        if user_auth:
            headers["X-User-Auth"] = json.dumps(user_auth.model_dump())
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}{endpoint}",
                    params=params or {},
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API client request failed: {e}")
            #logger.error(response.json()['detail'])
            if "events" in endpoint:
                return []
            elif "communities" in endpoint:
                return []
            elif "streams" in endpoint:
                return []
            else:
                return {}
        except Exception as e:
            logger.error(f"Unexpected error in API client: {e}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}

api_client = APIClient()
