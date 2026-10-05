"""Supabase client construction for user and privileged database access."""

from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import settings


async def create_user_client(access_token: str) -> AsyncClient:
    """Create a request-scoped client whose queries are constrained by RLS."""
    options = AsyncClientOptions(
        auto_refresh_token=False,
        persist_session=False,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=options,
    )


async def create_service_role_client() -> AsyncClient:
    """Create a privileged backend client that bypasses RLS."""
    options = AsyncClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=options,
    )
