"""
User Management Routes - Admin Only

Provides comprehensive user management functionality:
- CRUD operations for users
- Role management
- Company access assignments
- User-company relationship management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.api.auth import UserAuth, require_admin
from backend.database import get_db
from backend.database.user_repository import UserRepository
from backend.database.company_repository import CompanyRepository

router = APIRouter(prefix="/users", tags=["User Management"])


# Pydantic models for request/response
class UserCreateRequest(BaseModel):
    """Request model for creating a user."""
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "user"


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_locked: bool
    last_login: Optional[str]
    created_at: str
    updated_at: Optional[str]


class UserListResponse(BaseModel):
    """Response model for user list."""
    items: List[UserResponse]
    total: int


class UserRoleUpdateRequest(BaseModel):
    """Request model for updating user role."""
    role: str


class UserActiveUpdateRequest(BaseModel):
    """Request model for updating user active status."""
    is_active: bool


class UserPasswordUpdateRequest(BaseModel):
    """Request model for updating user password."""
    password: str


class CompanyAccessRequest(BaseModel):
    """Request model for assigning company access."""
    company_id: int
    access_level: str = "read"  # read, write, admin


class CompanyAccessResponse(BaseModel):
    """Response model for company access."""
    user_id: int
    company_id: int
    access_level: str


class UserCompaniesResponse(BaseModel):
    """Response model for user's companies."""
    user_id: int
    username: str
    companies: List[dict]


class CompanyUsersResponse(BaseModel):
    """Response model for company's users."""
    company_id: str
    company_name: str
    users: List[dict]


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """List all users (admin only)."""
    user_repo = UserRepository(conn)
    users = user_repo.list_users()

    # Convert to response format
    items = [
        UserResponse(
            id=user["id"],
            username=user["username"],
            full_name=user.get("full_name"),
            role=user["role"],
            is_active=user["is_active"],
            is_locked=user["is_locked"],
            last_login=user["last_login"].isoformat() if user["last_login"] else None,
            created_at=user["created_at"].isoformat() if user["created_at"] else None,
            updated_at=user.get("updated_at").isoformat() if user.get("updated_at") else None
        )
        for user in users
    ]

    return UserListResponse(items=items, total=len(items))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Get user by ID (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        full_name=user.get("full_name"),
        role=user["role"],
        is_active=user["is_active"],
        is_locked=user["is_locked"],
        last_login=user["last_login"].isoformat() if user["last_login"] else None,
        created_at=user["created_at"].isoformat() if user["created_at"] else None,
        updated_at=user["updated_at"].isoformat() if user["updated_at"] else None
    )


@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
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

    from backend.api.auth import get_password_hash
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
        role=user["role"],
        is_active=True,
        is_locked=False,
        last_login=None,
        created_at=user["created_at"].isoformat(),
        updated_at=user["created_at"].isoformat()
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Update user details (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prepare update data
    update_data = {}
    if request.full_name is not None:
        update_data["full_name"] = request.full_name
    if request.role is not None:
        update_data["role"] = request.role.lower()
    if request.is_active is not None:
        update_data["is_active"] = request.is_active

    if update_data:
        # Update user
        sql = "UPDATE users SET "
        sql_parts = []
        params = []

        for field, value in update_data.items():
            sql_parts.append(f"{field} = %s")
            params.append(value)

        sql += ", ".join(sql_parts)
        sql += ", updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        params.append(user_id)

        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()

    # Return updated user
    updated_user = user_repo.get_user_by_id(user_id)
    return UserResponse(
        id=updated_user["id"],
        username=updated_user["username"],
        full_name=updated_user.get("full_name"),
        role=updated_user["role"],
        is_active=updated_user["is_active"],
        is_locked=updated_user["is_locked"],
        last_login=updated_user["last_login"].isoformat() if updated_user["last_login"] else None,
        created_at=updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        updated_at=updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    request: UserRoleUpdateRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Update user role (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sql = "UPDATE users SET role = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, (request.role.lower(), user_id))
        conn.commit()

    # Return updated user
    updated_user = user_repo.get_user_by_id(user_id)
    return UserResponse(
        id=updated_user["id"],
        username=updated_user["username"],
        full_name=updated_user.get("full_name"),
        role=updated_user["role"],
        is_active=updated_user["is_active"],
        is_locked=updated_user["is_locked"],
        last_login=updated_user["last_login"].isoformat() if updated_user["last_login"] else None,
        created_at=updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        updated_at=updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None
    )


@router.patch("/{user_id}/active", response_model=UserResponse)
async def update_user_active_status(
    user_id: int,
    request: UserActiveUpdateRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Update user active status (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update active status
    sql = "UPDATE users SET is_active = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, (request.is_active, user_id))
        conn.commit()

    # Return updated user
    updated_user = user_repo.get_user_by_id(user_id)
    return UserResponse(
        id=updated_user["id"],
        username=updated_user["username"],
        full_name=updated_user.get("full_name"),
        role=updated_user["role"],
        is_active=updated_user["is_active"],
        is_locked=updated_user["is_locked"],
        last_login=updated_user["last_login"].isoformat() if updated_user["last_login"] else None,
        created_at=updated_user["created_at"].isoformat() if updated_user["created_at"] else None,
        updated_at=updated_user["updated_at"].isoformat() if updated_user["updated_at"] else None
    )


@router.patch("/{user_id}/password")
async def update_user_password(
    user_id: int,
    request: UserPasswordUpdateRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Update user password (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from backend.api.auth import get_password_hash
    password_hash = get_password_hash(request.password)

    # Update password
    user_repo.update_password(user_id, password_hash)

    return {"message": "Password updated successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Delete user by deactivating (admin only)."""
    user_repo = UserRepository(conn)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Instead of deleting, deactivate the user
    sql = "UPDATE users SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        conn.commit()

    return {"message": f"User {user_id} deactivated successfully"}


# Company Access Management Routes
@router.get("/{user_id}/companies", response_model=UserCompaniesResponse)
async def get_user_companies(
    user_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Get all companies a user has access to (admin only)."""
    user_repo = UserRepository(conn)
    companies = user_repo.get_user_companies(user_id)

    # Get user info
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserCompaniesResponse(
        user_id=user_id,
        username=user["username"],
        companies=companies
    )


@router.post("/{user_id}/companies", response_model=CompanyAccessResponse)
async def assign_company_to_user(
    user_id: int,
    request: CompanyAccessRequest,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Assign a company to a user (admin only)."""
    user_repo = UserRepository(conn)
    company_repo = CompanyRepository(conn)

    # Verify user exists
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify company exists
    company = company_repo.get_company_by_tax_code(str(request.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Assign company to user
    user_repo.assign_company_to_user(user_id, request.company_id, request.access_level)

    return CompanyAccessResponse(
        user_id=user_id,
        company_id=request.company_id,
        access_level=request.access_level
    )


@router.delete("/{user_id}/companies/{company_id}")
async def remove_company_from_user(
    user_id: int,
    company_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Remove a company assignment from a user (admin only)."""
    user_repo = UserRepository(conn)

    # Verify user exists
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove company assignment
    user_repo.remove_company_from_user(user_id, company_id)

    return {"message": f"Company {company_id} removed from user {user_id}"}


@router.get("/companies/{company_id}/users", response_model=CompanyUsersResponse)
async def get_company_users(
    company_id: int,
    current_user: UserAuth = Depends(require_admin),
    conn=Depends(get_db)
):
    """Get all users with access to a specific company (admin only)."""
    user_repo = UserRepository(conn)
    company_repo = CompanyRepository(conn)

    # Verify company exists
    company = company_repo.get_company_by_tax_code(str(company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    users = user_repo.get_company_users(company_id)

    return CompanyUsersResponse(
        company_id=str(company_id),
        company_name=company.get("company_name", f"Company {company_id}"),
        users=users
    )