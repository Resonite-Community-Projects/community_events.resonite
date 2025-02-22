import os
import requests

from resonite_communities.utils.logger import get_logger

logger = get_logger('community_events')

geoip_db_path = "GeoLite2-Country.mmdb"
geoip_db_url = "https://github.com/P3TERX/GeoLite.mmdb/releases/latest/download/GeoLite2-Country.mmdb"

def get_geoip_db_path():

    if not os.path.exists(geoip_db_path):
        logger.info(f"{geoip_db_path} not found. Downloading...")
        response = requests.get(geoip_db_url)
        response.raise_for_status()
        with open(geoip_db_path, 'wb') as f:
            f.write(response.content)

    return geoip_db_path