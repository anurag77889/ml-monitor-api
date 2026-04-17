from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import CredentialsException, InactiveUserException
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

# Extracts Bearer token from the Authorization header
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency injected into any protected route.
    Decodes the JWT, loads the user from DB, returns them.
    Raises 401 if token is missing, invalid, or expired.
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise CredentialsException

    user = db.query(User).filter(User.id == int(user_id)).first()

    if user is None:
        raise CredentialsException

    if not user.is_active:
        raise InactiveUserException

    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Use this dependency for admin-only routes.
    """
    if not current_user.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException
    return current_user
