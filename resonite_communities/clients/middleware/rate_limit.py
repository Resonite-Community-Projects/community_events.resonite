import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from resonite_communities.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using semaphores to limit concurrent requests.
    
    This prevents database connection pool exhaustion by rejecting requests
    when too many concurrent requests are already being processed.
    """
    
    def __init__(self, app, max_concurrent_requests: int = 50):
        super().__init__(app)
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._active_requests = 0
        self._rejected_requests = 0
        logger.info(
            f"RateLimitMiddleware initialized with max_concurrent_requests={max_concurrent_requests}"
        )
    
    async def dispatch(self, request: Request, call_next):
        # Wait for semaphore to become available (queue requests)
        # This will naturally queue requests when the limit is reached
        # instead of rejecting them with 429 errors
        async with self.semaphore:
            self._active_requests += 1
            try:
                response = await call_next(request)
                return response
            finally:
                self._active_requests -= 1
