"""Supabase persistence operations for chat threads and messages."""

from typing import Any
from uuid import UUID, uuid4

from app.database.supabase import create_service_role_client, create_user_client


async def list_threads(access_token: str) -> list[dict[str, Any]]:
    client = await create_user_client(access_token)
    try:
        response = await (
            client.table("chat_threads")
            .select("id,title,created_at,updated_at")
            .order("updated_at", desc=True)
            .execute()
        )
        return response.data
    finally:
        await client.postgrest.aclose()
        await client.auth.close()


async def create_thread(access_token: str, user_id: UUID, title: str) -> dict[str, Any]:
    client = await create_user_client(access_token)
    try:
        response = await (
            client.table("chat_threads")
            .insert(
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "title": title,
                }
            )
            .execute()
        )
        return response.data[0]
    finally:
        await client.postgrest.aclose()
        await client.auth.close()


async def get_thread_owner(thread_id: UUID) -> UUID | None:
    client = await create_service_role_client()
    try:
        response = await (
            client.table("chat_threads")
            .select("user_id")
            .eq("id", str(thread_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return UUID(response.data[0]["user_id"])
    finally:
        await client.postgrest.aclose()
        await client.auth.close()


async def load_messages(access_token: str, thread_id: UUID) -> list[dict[str, Any]]:
    client = await create_user_client(access_token)
    try:
        response = await (
            client.table("chat_messages")
            .select("id,role,parts")
            .eq("thread_id", str(thread_id))
            .order("message_index")
            .execute()
        )
        return response.data
    finally:
        await client.postgrest.aclose()
        await client.auth.close()


async def append_chat_turn(
    access_token: str,
    thread_id: UUID,
    user_message_id: UUID,
    user_content: str,
    user_parts: list[dict[str, str]],
    assistant_message_id: UUID,
    assistant_content: str,
    assistant_parts: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> None:
    client = await create_user_client(access_token)
    try:
        await client.rpc(
            "append_chat_turn",
            {
                "p_thread_id": str(thread_id),
                "p_user_message_id": str(user_message_id),
                "p_assistant_message_id": str(assistant_message_id),
                "p_user_content": user_content,
                "p_user_parts": user_parts,
                "p_assistant_content": assistant_content,
                "p_assistant_parts": assistant_parts,
                "p_citations": citations,
            },
        ).execute()
    finally:
        await client.postgrest.aclose()
        await client.auth.close()
