import requests


def get_current_user(access_token):
    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
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
    return response.json()


def get_user_roles_in_guild_safe(access_token, guild_id):
    url = f"https://discord.com/api/v10/users/@me/guilds/{guild_id}/member"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if not "roles" in response.json():
        print(response.json())
        roles = []
    else:
        roles = response.json()["roles"]
    return {"ids": roles}
