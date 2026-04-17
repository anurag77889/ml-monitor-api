from sqlalchemy.orm import Session

from app.core.exceptions import CredentialsException, DuplicateException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Registers a new user.
    Checks for duplicate email/username before creating.
    """
    if get_user_by_email(db, payload.email):
        raise DuplicateException  # 409 Conflict

    if get_user_by_username(db, payload.username):
        raise DuplicateException

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # Reload from DB to get generated ID
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verifies email + password.
    Returns the user or raises 401.
    """
    user = get_user_by_email(db, email)

    if not user or not verify_password(password, user.hashed_password):
        raise CredentialsException  # Don't reveal which was wrong

    return user
