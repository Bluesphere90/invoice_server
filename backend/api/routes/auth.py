"""
Authentication routes for login/logout.
"""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    Token,
    UserAuth,
    require_admin
)
from backend.config import settings
from backend.database import get_db
from backend.database.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    full_name: Optional[str]
    role: str


class CreateUserRequest(BaseModel):
    """Create user request (admin only)."""
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, conn=Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_username(request.username)
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.get("is_locked"):
        logger.warning(f"Login attempt for locked account: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked due to too many failed attempts. Contact administrator.",
        )
    
    # Check if account is active
    if not user.get("is_active"):
        logger.warning(f"Login attempt for inactive account: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        user_repo.increment_failed_login(user["id"])
        logger.warning(f"Invalid password for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Successful login
    user_repo.update_login_success(user["id"])
    
    # Create token
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"]
        }
    )
    
    logger.info(f"User logged in: {request.username}")
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserAuth = Depends(get_current_user),
    conn=Depends(get_db)
):
    """Get current authenticated user info."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(current_user.id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user["id"],
        username=user["username"],
        full_name=user.get("full_name"),
        role=(user["role"] or "user").lower()
    )


@router.get("/companies")
async def get_my_companies(
    current_user: UserAuth = Depends(get_current_user),
    conn=Depends(get_db)
):
    """Get companies the current user has access to."""
    user_repo = UserRepository(conn)
    
    # Admins can see all companies
    if current_user.role == "admin":
        from backend.database.company_repository import CompanyRepository
        company_repo = CompanyRepository(conn)
        return company_repo.list_companies()
    
    return user_repo.get_user_companies(current_user.id)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserAuth = Depends(get_current_user),
    conn=Depends(get_db)
):
    """Change current user's password."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(current_user.id)
    
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    new_hash = get_password_hash(request.new_password)
    user_repo.update_password(current_user.id, new_hash)
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}


# =====================================================
# ADMIN ROUTES
# =====================================================

@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Create a new user (admin only)."""
    user_repo = UserRepository(conn)
    
    # Check if username exists
    existing = user_repo.get_user_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    password_hash = get_password_hash(request.password)
    user = user_repo.create_user(
        username=request.username,
        password_hash=password_hash,
        full_name=request.full_name,
        role=request.role.lower()
    )
    
    return UserResponse(
        id=user["id"],
        username=user["username"],
        full_name=user.get("full_name"),
        role=user["role"]
    )


@router.get("/users")
async def list_users(
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """List all users (admin only)."""
    user_repo = UserRepository(conn)
    return user_repo.list_users()


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Unlock a locked user account (admin only)."""
    user_repo = UserRepository(conn)
    user_repo.unlock_user(user_id)
    return {"message": f"User {user_id} unlocked"}


@router.post("/users/{user_id}/companies/{company_id}")
async def assign_company_to_user(
    user_id: int,
    company_id: int,
    access_level: str = "read",
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Assign a company to a user (admin only)."""
    user_repo = UserRepository(conn)
    user_repo.assign_company_to_user(user_id, company_id, access_level)
    return {"message": f"Company {company_id} assigned to user {user_id}"}


@router.delete("/users/{user_id}/companies/{company_id}")
async def remove_company_from_user(
    user_id: int,
    company_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Remove a company assignment from a user (admin only)."""
    user_repo = UserRepository(conn)
    user_repo.remove_company_from_user(user_id, company_id)
    return {"message": f"Company {company_id} removed from user {user_id}"}
