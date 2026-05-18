"""
Authentication and authorization utilities.

Improvements over previous version:
- Uses bcrypt via passlib instead of raw hashlib (proper salt management)
- SECRET_KEY pulled from centralized config (not hardcoded)
- Token payload includes role for fast RBAC checks
- Dependency functions raise typed exceptions, not raw HTTPExceptions
- Rate limiting hooks ready (middleware integration)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.session import get_db
from backend.db import models
from backend.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Password hashing (bcrypt) ────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash. Handles legacy hashlib format too."""
    # Support legacy format: salt$key_hex (from previous pbkdf2_hmac implementation)
    if "$" in hashed_password and len(hashed_password.split("$")) == 2:
        import hashlib
        import secrets
        try:
            salt, key_hex = hashed_password.split("$")
            key = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000
            )
            return secrets.compare_digest(key.hex(), key_hex)
        except Exception:
            return False

    return pwd_context.verify(plain_password, hashed_password)


# ── JWT tokens ───────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with user ID and role in payload."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises AuthenticationError on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("sub") is None:
            raise AuthenticationError()
        return payload
    except JWTError:
        raise AuthenticationError()


# ── FastAPI dependencies ─────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Extract and validate the current user from the JWT bearer token."""
    payload = decode_token(token)
    user_id = int(payload["sub"])

    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.is_active == True,
    ).first()

    if user is None:
        raise AuthenticationError("User account not found or deactivated.")

    return user


def require_role(*roles: str):
    """
    Role-based access control dependency factory.

    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user = Depends(require_role("instructor"))):
            ...
    """
    async def role_checker(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        if current_user.role not in roles:
            raise AuthorizationError(
                f"This action requires one of: {', '.join(roles)}. "
                f"Your role: {current_user.role}"
            )
        return current_user

    return role_checker
