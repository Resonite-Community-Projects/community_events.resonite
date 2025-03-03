import hashlib
import contextlib
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from datetime import datetime
import geoip2.database
from apachelogs import LogParser

from resonite_communities.clients.models.metrics import Metrics
from resonite_communities.auth.db import get_async_session
from resonite_communities.clients.models.metrics import ClientType

parser = LogParser("%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"")

monitored_routes = [
    '/',
    '/streams',
    '/v1/events',
    '/v1/aggregated_events',
    '/v2/events',
]

bot_keywords = [
    "bot", "spider", "crawl", "robot", "searchbot", "crawler", "bot/", "slurp", "baidu",
    "googlebot", "bingbot", "duckduckbot", "yandexbot", "facebookexternalhit", "twitterbot",
    "instagram", "ai", "crawler", "archive.org", "wget", "scrapy"
]
browser_keywords = [
    "chrome", "firefox", "safari", "edge", "opera", "trident", "gecko", "applewebkit",
    "msie", "edge", "yandex", "brave", "vivaldi", "mozilla"
]
tool_keywords = [
    "curl", "python", "dart", "requests", "node", "go-http-client", "okhttp", "postman",
    "insomnia", "urllib", "fetch", "http-client", "libwww-perl", "wget", "axios", "artillery",
    "httpie", "rest-client", "api-client"
]
mobile_keywords = [
    "android", "iphone", "ipad", "mobile", "blackberry", "windows phone"
]

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

        user_agent = request.headers.get('User-Agent')
        is_bot = any(keyword.lower() in user_agent.lower() for keyword in bot_keywords)
        is_resonite = "resonite" in user_agent.lower()
        is_neos = "neos" in user_agent.lower()
        is_browser = any(keyword.lower() in user_agent.lower() for keyword in browser_keywords)
        is_tool = any(keyword.lower() in user_agent.lower() for keyword in tool_keywords)
        is_mobile = any(keyword.lower() in user_agent.lower() for keyword in mobile_keywords)
        client = None
        if is_bot:
            client = ClientType.BOT
        elif is_neos:
            client = ClientType.NEOS
        elif is_resonite:
            client = ClientType.RESONITE
        elif is_tool:
            client = ClientType.TOOL
        elif is_mobile:
            client = ClientType.BROWSER_MOBILE
        elif is_browser:
            client = ClientType.BROWSER_DESKTOP

        metrics = Metrics(
            endpoint=request.url.path,
            domain=request.url.hostname,
            hashed_ip=hashed_ip,
            country=country,
            version=version,
            client=client,
            user_agent=user_agent,
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