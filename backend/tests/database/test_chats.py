from types import SimpleNamespace
from uuid import UUID

import pytest

from app.database import chats

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.mark.anyio
async def test_create_thread_supplies_primary_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inserted: dict[str, str] = {}

    class Query:
        def insert(self, payload: dict[str, str]) -> "Query":
            inserted.update(payload)
            return self

        async def execute(self) -> SimpleNamespace:
            return SimpleNamespace(data=[inserted])

    class Closeable:
        async def aclose(self) -> None:
            pass

        async def close(self) -> None:
            pass

    class Client:
        postgrest = Closeable()
        auth = Closeable()

        def table(self, name: str) -> Query:
            assert name == "chat_threads"
            return Query()

    async def fake_create_user_client(access_token: str) -> Client:
        assert access_token == "access-token"
        return Client()

    monkeypatch.setattr(chats, "create_user_client", fake_create_user_client)

    row = await chats.create_thread("access-token", USER_ID, "New conversation")

    assert UUID(inserted["id"])
    assert inserted["user_id"] == str(USER_ID)
    assert inserted["title"] == "New conversation"
    assert row == inserted


@pytest.mark.anyio
async def test_append_chat_turn_sends_citations_in_atomic_rpc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rpc_call: dict[str, object] = {}

    class Query:
        async def execute(self) -> SimpleNamespace:
            return SimpleNamespace(data=None)

    class Closeable:
        async def aclose(self) -> None:
            pass

        async def close(self) -> None:
            pass

    class Client:
        postgrest = Closeable()
        auth = Closeable()

        def rpc(self, name: str, payload: dict[str, object]) -> Query:
            rpc_call.update(name=name, payload=payload)
            return Query()

    async def fake_create_user_client(access_token: str) -> Client:
        return Client()

    monkeypatch.setattr(chats, "create_user_client", fake_create_user_client)
    citation = {
        "id": "33333333-3333-3333-3333-333333333333",
        "chunk_id": "44444444-4444-4444-4444-444444444444",
        "citation_index": 1,
        "excerpt": "supporting text",
    }

    await chats.append_chat_turn(
        "access-token",
        UUID("55555555-5555-5555-5555-555555555555"),
        UUID("66666666-6666-6666-6666-666666666666"),
        "question",
        [{"type": "text", "text": "question"}],
        UUID("77777777-7777-7777-7777-777777777777"),
        "answer [1]",
        [{"type": "text", "text": "answer [1]"}],
        [citation],
    )

    assert rpc_call["name"] == "append_chat_turn"
    assert rpc_call["payload"]["p_citations"] == [citation]
