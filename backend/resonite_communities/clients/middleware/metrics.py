import hashlib
import contextlib
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from datetime import datetime
import geoip2.database

from resonite_communities.clients.models.metrics import Metrics
from resonite_communities.auth.db import get_async_session

class MetricsMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, db_path):
        super().__init__(app)
        self.monitored_routes = [
            '/',
            '/streams',
            '/v1/events',
            '/v1/aggregated_events',
            '/v2/events',
        ]
        self.reader = geoip2.database.Reader(db_path)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path not in self.monitored_routes:
            return response

        ip_address = request.headers.get('X-Forwarded-For', request.client.host).split(",")[0]
        hashed_ip = hashlib.sha256(ip_address.encode()).hexdigest()

        country = self.get_country_from_ip(ip_address)
        query_params = parse_qs(request.url.query)
        version = query_params.get('clversion', [None])[0]

        metrics = Metrics(
            endpoint=request.url.path,
            domain=request.url.hostname,
            hashed_ip=hashed_ip,
            country=country,
            version=version,
            timestamp=datetime.utcnow(),
        )

        get_async_session_context = contextlib.asynccontextmanager(get_async_session)

        async with get_async_session_context() as session:
            session.add(metrics)
            await session.commit()

        return response

    def get_country_from_ip(self, ip):
        try:
            response = self.reader.country(ip)
            return response.country.name
        except Exception:
            return "Unknown"