"""Authentication verification routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthenticatedUserResponse(BaseModel):
    id: UUID
    email: str


@router.get("/me")
async def get_authenticated_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AuthenticatedUserResponse:
    """Return the identity represented by a valid bearer token."""
    return AuthenticatedUserResponse(id=user.id, email=user.email)
