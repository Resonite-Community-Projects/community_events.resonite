import hashlib
import contextlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from datetime import datetime
import geoip2.database
from resonite_communities.clients.web.models.metrics import Metrics
from resonite_communities.auth.db import get_async_session

class MetricsMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, db_path):
        super().__init__(app)
        self.monitored_routes = [
            '/',
            '/streams',
        ]
        self.reader = geoip2.database.Reader(db_path)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path not in self.monitored_routes:
            return response

        ip_address = request.headers.get('X-Forwarded-For', request.client.host).split(",")[0]
        import logging
        hashed_ip = hashlib.sha256(ip_address.encode()).hexdigest()

        country = self.get_country_from_ip(ip_address)
        logging.error(ip_address)
        logging.error(ip_address.encode())
        logging.error(hashed_ip)
        logging.error(country)

        metrics = Metrics(
            endpoint=request.url.path,
            domain=request.url.hostname,
            hashed_ip=hashed_ip,
            country=country,
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