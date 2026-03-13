from fastapi import APIRouter, HTTPException, status, Query
from typing import List

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import ResponseModel
from app.services import user as user_service
from app.utils.exceptions import NotFoundException, ConflictException

router = APIRouter()


def serialize_user(user: dict) -> dict:
    """Serialize user document for response."""
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
        "full_name": user.get("full_name"),
        "is_active": user["is_active"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.post("", response_model=ResponseModel[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    # Check if email already exists
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise ConflictException(detail="Email already registered")
    
    # Check if username already exists
    existing_user = await user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise ConflictException(detail="Username already taken")
    
    user = await user_service.create_user(user_data)
    
    return ResponseModel(
        message="User created successfully",
        data=serialize_user(user)
    )


@router.get("", response_model=ResponseModel[List[UserResponse]])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Get list of users."""
    users = await user_service.get_users(skip=skip, limit=limit)
    
    return ResponseModel(
        message="Users retrieved successfully",
        data=[serialize_user(user) for user in users]
    )


@router.get("/{user_id}", response_model=ResponseModel[UserResponse])
async def get_user(user_id: str):
    """Get user by ID."""
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise NotFoundException(detail="User not found")
    
    return ResponseModel(
        message="User retrieved successfully",
        data=serialize_user(user)
    )


@router.put("/{user_id}", response_model=ResponseModel[UserResponse])
async def update_user(user_id: str, user_data: UserUpdate):
    """Update user."""
    # Check if user exists
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise NotFoundException(detail="User not found")
    
    # Check email uniqueness if being updated
    if user_data.email and user_data.email != existing_user["email"]:
        email_user = await user_service.get_user_by_email(user_data.email)
        if email_user:
            raise ConflictException(detail="Email already registered")
    
    # Check username uniqueness if being updated
    if user_data.username and user_data.username != existing_user["username"]:
        username_user = await user_service.get_user_by_username(user_data.username)
        if username_user:
            raise ConflictException(detail="Username already taken")
    
    user = await user_service.update_user(user_id, user_data)
    
    return ResponseModel(
        message="User updated successfully",
        data=serialize_user(user)
    )


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(user_id: str):
    """Delete user."""
    deleted = await user_service.delete_user(user_id)
    
    if not deleted:
        raise NotFoundException(detail="User not found")
    
    return ResponseModel(message="User deleted successfully")
