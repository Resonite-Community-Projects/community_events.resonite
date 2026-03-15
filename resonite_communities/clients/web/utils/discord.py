import requests

from resonite_communities.utils.logger import get_logger

def _parse_error(response):
    try:
        dict_error = response.json()
        if 'error' not in dict_error.keys() or 'message' not in dict_error.keys():
            return f"{response.status_code} - {response.text}"
        return f"{response.status_code} - {dict_error['error']} - {dict_error['message']}"
    except Exception:
        return f"{response.status_code}"

def get_current_user(access_token):
    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        get_logger("get_user_roles_in_guild_safe").error(f"Error when getting user information: {_parse_error(response)}")
    user_data = response.json()

    # Construct the avatar URL
    avatar_hash = user_data.get('avatar')
    user_id = user_data.get('id')

    if avatar_hash:
        # Determine if the avatar is animated
        is_animated = avatar_hash.startswith("a_")
        extension = "gif" if is_animated else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{
            user_id}/{avatar_hash}.{extension}"
    else:
        # Fallback to the default avatar
        default_avatar = int(user_id) % 5
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{
            default_avatar}.png"

    user_data['avatar_url'] = avatar_url
    return user_data


def get_user_guilds(access_token):
    url = "https://discord.com/api/v10/users/@me/guilds"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        get_logger("get_user_roles_in_guild_safe").error(f"Error when getting user information: {_parse_error(response)}")
    return response.json()


def get_user_roles_in_guild_safe(access_token, guild_id):
    url = f"https://discord.com/api/v10/users/@me/guilds/{guild_id}/member"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        get_logger("get_user_roles_in_guild_safe").error(f"Error when getting user information: {_parse_error(response)}")
    roles = []
    retry_after = 0
    if "roles" in response.json():
        roles = response.json()["roles"]
    if "retry_after" in response.json():
        retry_after = response.json()["retry_after"]
    if not roles and not retry_after:
        get_logger("get_user_roles_in_guild_safe").error("Something is wrong when getting user roles in guild!")
    return roles, retry_after
