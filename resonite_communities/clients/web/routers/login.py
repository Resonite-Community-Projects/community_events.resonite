from fastapi import APIRouter
from starlette.responses import JSONResponse, RedirectResponse
from fastapi_users.router.oauth import generate_state_token

from resonite_communities.clients.web.auth import oauth_clients
from resonite_communities.utils import Config

router = APIRouter()

@router.get('/auth/login/{provider}')
async def login(provider: str):
    oauth_client = oauth_clients.get(provider)
    if not oauth_client:
        return JSONResponse({"error": f"Unsupported provider: {provider}"}, status_code=400)

    state_data: dict[str, str] = {}
    state_token = generate_state_token(state_data, Config.SECRET)

    authorization_url = await oauth_client["client"].get_authorization_url(
        redirect_uri=oauth_client["redirect_uri"],
        state=state_token,
    )

    return RedirectResponse(authorization_url)