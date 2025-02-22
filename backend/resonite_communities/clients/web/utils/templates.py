from starlette.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from resonite_communities.clients.web.utils import filters

env = Environment(loader=FileSystemLoader("resonite_communities/clients/web/templates"))

env.filters["formatdatetime"] = filters.format_datetime
env.filters["detect_location"] = filters.detect_resonite_url
env.filters["detect_community"] = filters.detect_resonite_community
env.filters["parse"] = filters.parse_desciption
env.filters["tab_is_active"] = filters.filter_tab_is_active
env.filters["tab_display"] = filters.filter_tab_display
env.filters["tags"] = filters.filter_tag
env.filters["format_seconds"] = filters.format_seconds

templates = Jinja2Templates(env=env)