"""FastAPI dependencies for Supabase bearer-token authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError

from app.database.supabase import (
    create_service_role_client,
    create_user_client,
)

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Authenticated user identity made available to request handlers."""

    id: UUID
    email: str
    access_token: str


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Verify a Supabase access token and provision its application user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    client = await create_user_client(credentials.credentials)
    try:
        try:
            response = await client.auth.get_user(credentials.credentials)
        except AuthApiError as error:
            raise unauthorized() from error
    finally:
        await client.auth.close()

    if response is None or response.user is None or response.user.email is None:
        raise unauthorized()

    user = CurrentUser(
        id=response.user.id,
        email=response.user.email,
        access_token=credentials.credentials,
    )
    service_client = await create_service_role_client()
    try:
        await (
            service_client.table("users")
            .upsert({"id": str(user.id), "email": user.email}, on_conflict="id")
            .execute()
        )
    finally:
        await service_client.postgrest.aclose()
        await service_client.auth.close()

    return user
