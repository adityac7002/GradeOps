"""
Auth endpoints — v1.

Login, logout (token invalidation via client), current user, health check.
All responses are typed. Rate limiting is enforced via middleware.
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.schemas import LoginRequest, TokenResponse, UserOut
from backend.db.repositories import UserRepository
from backend.core.security import verify_password, create_access_token, get_current_user
from backend.exceptions import AuthenticationError
from backend.db import models

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate with email + password. Returns a JWT bearer token.

    Rate limited: 10 requests/minute per IP (enforced in middleware).
    """
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)

    if not user or not verify_password(payload.password, user.password_hash):
        # Generic message to prevent email enumeration
        raise AuthenticationError("Incorrect email or password.")

    token = create_access_token(user_id=user.id, role=user.role)
    logger.info("User %d (%s) logged in from %s", user.id, user.email, request.client.host if request.client else "unknown")

    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
