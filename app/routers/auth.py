from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.token import TokenResponse
from app.services.auth_service import create_user, authenticate_user
from app.core.security import create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    user = create_user(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Login and receive a JWT access token."""
    user = authenticate_user(db, payload.email, payload.password)
    token = create_access_token(subject=user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user