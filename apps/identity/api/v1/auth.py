from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.identity.application.auth_service import AuthService
from apps.identity.infrastructure.database import get_db_session
from apps.identity.infrastructure.keycloak_client import KeycloakClient

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RefreshRequest(BaseModel):
    refresh_token : str

@router.post("/login")
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db_session)
    ):
    keycloak_client = KeycloakClient()
    auth_service = AuthService(db, keycloak_client)

    try:
        tokens = auth_service.handle_login(form_data.username, form_data.password)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": tokens["expires_in"],
            "token_type": "Bearer"
        }
    except Exception:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Authentication failed"
        )

@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db_session)):
    keycloak_client = KeycloakClient()
    auth_service = AuthService(db, keycloak_client)
    try:
        tokens = auth_service.handle_refresh(payload.refresh_token)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_in": tokens["expires_in"],
            "token_type": "Bearer"
        }
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token transformation")