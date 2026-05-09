from typing import Any
from fastapi import APIRouter
from backend.api.deps import CurrentUser
from backend.schemas.user import UserResponse

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser) -> Any:
    # Contar numero de conversas
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        conversations_count=len(current_user.conversations)
    )
