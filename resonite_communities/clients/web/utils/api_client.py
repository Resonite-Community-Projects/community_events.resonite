import httpx
from typing import Dict, Any, Optional
from resonite_communities.utils.config import ConfigManager
from resonite_communities.utils.logger import get_logger
from resonite_communities.clients.utils.auth import UserAuthModel
import json
import traceback
import hashlib
from datetime import datetime, timedelta

config_manager = ConfigManager()
logger = get_logger('WebAPIClient')

# Simple in-memory cache with TTL
class ResponseCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, endpoint: str, params: Optional[Dict], user_auth: Optional[UserAuthModel]) -> str:
        """Generate a unique cache key based on endpoint, params, and user auth."""
        key_parts = [endpoint]
        if params:
            key_parts.append(str(sorted(params.items())))
        if user_auth:
            if user_auth.is_superuser:
                key_parts.append("superuser")
            elif user_auth.discord_account:
                communities = sorted(user_auth.discord_account.user_communities or [])
                key_parts.append(f"communities:{','.join(communities)}")
            else:
                key_parts.append("authenticated")
        else:
            key_parts.append("anonymous")
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    def get(self, endpoint: str, params: Optional[Dict], user_auth: Optional[UserAuthModel]):
        """Get cached response if not expired."""
        key = self._generate_key(endpoint, params, user_auth)
        if key in self.cache:
            data, expiry = self.cache[key]
            if datetime.utcnow() < expiry:
                logger.debug(f"Cache HIT for {endpoint}")
                return data
            else:
                del self.cache[key]
                logger.debug(f"Cache EXPIRED for {endpoint}")
        logger.debug(f"Cache MISS for {endpoint}")
        return None
    
    def set(self, endpoint: str, params: Optional[Dict], user_auth: Optional[UserAuthModel], data):
        """Cache response with TTL."""
        key = self._generate_key(endpoint, params, user_auth)
        expiry = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        self.cache[key] = (data, expiry)
        logger.debug(f"Cache SET for {endpoint} (TTL: {self.ttl_seconds}s)")

class APIClient:
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self, cache_ttl: int = 300):
        self.api_url = config_manager.infrastructure_config.API_CLIENT_URL
        self.cache = ResponseCache(ttl_seconds=cache_ttl)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client with connection pooling."""
        if self._client is None:
            limits = httpx.Limits(
                max_keepalive_connections=50,
                max_connections=200,
                keepalive_expiry=30.0
            )
            self._client = httpx.AsyncClient(limits=limits, timeout=60.0)
        return self._client

    async def close(self):
        """Close the shared HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, user_auth: Optional[UserAuthModel] = None, use_cache: bool = True):
        # Check cache first (if caching is enabled)
        if use_cache:
            cached_data = self.cache.get(endpoint, params, user_auth)
            if cached_data is not None:
                return cached_data
        
        headers = {}
        if user_auth:
            headers["X-User-Auth"] = json.dumps(user_auth.model_dump())
        
        response = None
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.api_url}{endpoint}",
                params=params or {},
                headers=headers
            )
            response.raise_for_status()
            
            # Validate response before parsing JSON
            if not response.content:
                logger.error(f"API returned empty response for {endpoint} (status: {response.status_code})")
                return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
            result = response.json()
            # Cache successful response (if caching is enabled)
            if use_cache:
                self.cache.set(endpoint, params, user_auth, result)
            return result
            
        except httpx.TimeoutException as e:
            logger.error(f"API request timeout for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.debug(f"Timeout traceback: {traceback.format_exc()}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API HTTP error for {endpoint}: {e.response.status_code} - {str(e)}")
            if response:
                try:
                    logger.error(f"Response detail: {response.json()}")
                except:
                    logger.error(f"Response text: {response.text[:500]}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
        except json.JSONDecodeError as e:
            logger.error(f"API JSON decode error for {endpoint}: {str(e)}")
            if response:
                logger.error(f"Response status: {response.status_code}, Content preview: {response.text[:500]}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
        except httpx.ConnectError as e:
            logger.error(f"API connection error for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.debug(f"Connection error traceback: {traceback.format_exc()}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
        except httpx.HTTPError as e:
            logger.error(f"API HTTP error for {endpoint}: {type(e).__name__}: {str(e)}")
            if response:
                logger.error(f"Response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
            logger.debug(f"HTTP error traceback: {traceback.format_exc()}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}
            
        except Exception as e:
            logger.error(f"Unexpected error in API client for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return [] if any(x in endpoint for x in ["events", "communities", "streams"]) else {}

    async def post(self, endpoint: str, data: Dict[str, Any], user_auth: Optional[UserAuthModel] = None):
        headers = {
            "Content-Type": "application/json"
        }
        if user_auth:
            headers["X-User-Auth"] = json.dumps(user_auth.model_dump())

        response = None
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.api_url}{endpoint}",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            # Validate response before parsing JSON
            if not response.content:
                logger.error(f"API POST returned empty response for {endpoint} (status: {response.status_code})")
                return {"error": "Empty response"}
            
            return response.json()
            
        except httpx.TimeoutException as e:
            logger.error(f"API POST timeout for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.debug(f"Timeout traceback: {traceback.format_exc()}")
            return {"error": f"Request timeout: {str(e)}"}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API POST HTTP error for {endpoint}: {e.response.status_code} - {str(e)}")
            if response:
                try:
                    logger.error(f"Response detail: {response.json()}")
                except:
                    logger.error(f"Response text: {response.text[:500]}")
            return {"error": f"HTTP {e.response.status_code}: {str(e)}"}
            
        except json.JSONDecodeError as e:
            logger.error(f"API POST JSON decode error for {endpoint}: {str(e)}")
            if response:
                logger.error(f"Response status: {response.status_code}, Content preview: {response.text[:500]}")
            return {"error": f"Invalid JSON response: {str(e)}"}
            
        except httpx.HTTPError as e:
            logger.error(f"API POST HTTP error for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.debug(f"HTTP error traceback: {traceback.format_exc()}")
            return {"error": str(e)}
            
        except Exception as e:
            logger.error(f"Unexpected error in API POST for {endpoint}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"error": str(e)}

api_client = APIClient()
