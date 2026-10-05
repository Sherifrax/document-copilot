"""Authenticated chat thread and streaming routes."""

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from httpx import HTTPError
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field, field_validator

from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import (
    ChatStreamRequest,
    TextPart,
    UIMessage,
    stored_message_to_ui_message,
    user_message_content,
)
from app.chat.streaming import STUB_REPLY, stream_stubbed_reply
from app.database.chats import (
    append_chat_turn,
    create_thread,
    get_thread_owner,
    list_threads,
    load_messages,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class CreateThreadRequest(BaseModel):
    title: str = Field(default="New chat", max_length=200)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


def database_failure() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The chat database is unavailable",
    )


async def require_thread_owner(thread_id: UUID, user_id: UUID) -> None:
    try:
        owner_id = await get_thread_owner(thread_id)
    except (APIError, HTTPError) as error:
        raise database_failure() from error

    if owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found"
        )
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this chat thread",
        )


@router.get("/threads")
async def get_threads(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ThreadResponse]:
    try:
        rows = await list_threads(user.access_token)
    except (APIError, HTTPError) as error:
        raise database_failure() from error
    return [ThreadResponse.model_validate(row) for row in rows]


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def post_thread(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    request: CreateThreadRequest | None = None,
) -> ThreadResponse:
    request = request or CreateThreadRequest()
    try:
        row = await create_thread(user.access_token, user.id, request.title)
    except (APIError, HTTPError) as error:
        raise database_failure() from error
    return ThreadResponse.model_validate(row)


@router.get("/threads/{thread_id}/messages")
async def get_messages(
    thread_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[UIMessage]:
    await require_thread_owner(thread_id, user.id)
    try:
        rows = await load_messages(user.access_token, thread_id)
    except (APIError, HTTPError) as error:
        raise database_failure() from error
    return [stored_message_to_ui_message(row) for row in rows]


@router.post("/stream")
async def post_chat_stream(
    request: ChatStreamRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    await require_thread_owner(request.id, user.id)

    user_message = request.messages[-1]
    user_content = user_message_content(user_message)
    user_parts = [part.model_dump() for part in user_message.parts]
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    assistant_parts = [TextPart(type="text", text=STUB_REPLY).model_dump()]

    async def persist_turn() -> None:
        await append_chat_turn(
            user.access_token,
            request.id,
            user_message_id,
            user_content,
            user_parts,
            assistant_message_id,
            STUB_REPLY,
            assistant_parts,
        )

    return StreamingResponse(
        stream_stubbed_reply(assistant_message_id, persist_turn),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )
