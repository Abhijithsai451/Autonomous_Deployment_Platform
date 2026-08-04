from typing import Dict, Any

from fastapi import Depends, HTTPException, status

import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from apps.identity.config.identity_settings import identity_settings as settings
from packages.auth.auth_user import AuthUser
from packages.logging.structured_logs import struc_logger

logger = struc_logger

security = HTTPBearer()

KEYCLOAK_URL = settings.KEYCLOAK_URL
KEYCLOAK_REALM = settings.KEYCLOAK_REALM

JWKS_URL = f"{KEYCLOAK_URL}/realm/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
jwks_client = jwt.PyJWKClient(JWKS_URL)


async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: dict = Depends(verify_jwt)) -> AuthUser:
    realm_roles = token.get("realm_access", {}).get("roles", [])

    return AuthUser(
        id=token.get("sub"),
        email=token.get("email"),
        username=token.get("preferred_username"),
        realm_roles=realm_roles,
    )