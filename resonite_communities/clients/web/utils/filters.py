import re
import traceback

from datetime import datetime
from resonite_communities.utils import logger

re_cloudx_url_match_compiled = re.compile('(http|https):\/\/cloudx.azurewebsites.net[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]')
re_url_match_compiled = re.compile('((?:http|https):\/\/[\w_-]+(?:(?:\.[\w_-]+)+)[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])')
re_discord_timestamp_match_compiled = re.compile('<t:(.*?)>')

def format_datetime(value, format="%d %b %I:%M %p"):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime(format)
    elif isinstance(value, str):
        try:
            dt_object = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            return dt_object.strftime(format)
        except ValueError:
            logger.error(f"Could not parse datetime string: {value}")
            return value
    return value

def detect_resonite_url(event):
    if event.get('location_web_session_url'):
        return "<a href='{}'>{}</a>".format(
            event.get('location_web_session_url'), event.get('location_str')
        )
    elif event.get('location_session_url'):
        return "<a href='{}'>{}</a>".format(
            event.get('location_session_url'), event.get('location_str')
        )
    return event.get('location_str')

def detect_resonite_community(event):
    if event.get('community_url'):
        return "<a href='{}'>{}</a>".format(
            event.get('community_url'), event.get('community_name')
        )
    return event.get('community_name')

def parse_desciption(desc):
    try:
        desc = re.sub(
            re_url_match_compiled,
            "<a href='\\1'>\\1</a>",
            desc)
    except Exception:
        logger.error(traceback.format_exc())
    desc = desc.replace('\n', '<br>')
    return desc

def filter_tab_is_active(tab, current_tab):
    if tab == current_tab:
        return "is-active"
    return ""

def filter_tab_display(tab, current_tab):
    if tab == current_tab:
        return "block"
    return "none"

def filter_tag(tags):
    html_tags = ""
    if not tags:
        return ""
    tags = tags.split(',')
    tags = [tag for tag in tags if tag not in ["public", "resonite"] and not tag.startswith('lang:')]
    for tag in tags:
        html_tags += f"<span class='tag is-info m-1'>{tag}</span>"
    return html_tags

def filter_flag(flags):
    html_flags = ""
    if not flags:
        return ""
    flags = flags.split(',')
    flags = [flag for flag in flags if flag.startswith('lang:')]
    for flag in flags:
        html_flags += f"<span class='tag flag is-info m-1'>{flag.split(':')[1]}</span>"
    return html_flags

def format_seconds(value: int) -> str:
    hours = value // 3600
    minutes = (value % 3600) // 60
    seconds = value % 60
    result = []
    if hours > 0:
        result.append(f"{hours}h")
    if minutes > 0:
        result.append(f"{minutes}min")
    if seconds > 0 or not result:
        result.append(f"{seconds}sec")
    return "".join(result)
