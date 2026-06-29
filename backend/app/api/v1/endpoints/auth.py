from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(email: str, password: str, full_name: str):
    """Register a new user account."""
    # TODO: Sprint 1 — implement user creation + hashed password
    return {"message": "User registered", "email": email}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and receive JWT access + refresh tokens."""
    # TODO: Sprint 1 — verify credentials, issue tokens
    return {"access_token": "placeholder", "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Exchange a refresh token for a new access token."""
    # TODO: Sprint 1
    return {"access_token": "placeholder", "token_type": "bearer"}


@router.post("/logout")
async def logout(refresh_token: str):
    """Invalidate the refresh token."""
    # TODO: Sprint 1
    return {"message": "Logged out"}
