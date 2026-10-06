import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import chat
from app.assistant.outputs import ValidatedGroundedAnswer
from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
THREAD_ID = UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
TEST_REPLY = "The corpus does not contain enough evidence."


class FakeOrchestrator:
    async def answer(self, **kwargs: object) -> ValidatedGroundedAnswer:
        return ValidatedGroundedAnswer(
            answer=TEST_REPLY,
            citations=(),
            cited_passages=(),
            insufficient_evidence=True,
        )


@pytest.fixture
def client() -> TestClient:
    async def authenticated_user() -> CurrentUser:
        return CurrentUser(
            id=USER_ID,
            email="analyst@example.com",
            access_token="access-token",
        )

    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[chat.get_chat_orchestrator] = FakeOrchestrator
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def parse_events(response_text: str) -> list[dict[str, object] | str]:
    events = []
    for block in response_text.strip().split("\n\n"):
        data = block.removeprefix("data: ")
        events.append(data if data == "[DONE]" else json.loads(data))
    return events


def thread_row(*, title: str = "New chat") -> dict[str, str]:
    return {
        "id": str(THREAD_ID),
        "title": title,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


def stream_body() -> dict[str, object]:
    return {
        "id": str(THREAD_ID),
        "messages": [
            {
                "id": "client-message-id",
                "role": "user",
                "parts": [{"type": "text", "text": "What changed?"}],
            }
        ],
        "trigger": "submit-message",
    }


def test_requires_authentication() -> None:
    with TestClient(app) as unauthenticated_client:
        response = unauthenticated_client.get("/chat/threads")

    assert response.status_code == 401


def test_cors_exposes_ai_sdk_stream_header() -> None:
    with TestClient(app) as browser_client:
        response = browser_client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )

    assert response.status_code == 200
    assert (
        response.headers["access-control-expose-headers"]
        == "x-vercel-ai-ui-message-stream"
    )


def test_list_threads(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    async def fake_list_threads(access_token: str) -> list[dict[str, str]]:
        assert access_token == "access-token"
        return [thread_row(title="Most recent")]

    monkeypatch.setattr(chat, "list_threads", fake_list_threads)

    response = client.get("/chat/threads")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Most recent"


@pytest.mark.parametrize(
    ("body", "expected_title"),
    [(None, "New chat"), ({"title": "  Earnings  "}, "Earnings")],
)
def test_create_thread(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    body: dict[str, str] | None,
    expected_title: str,
) -> None:
    async def fake_create_thread(
        access_token: str, user_id: UUID, title: str
    ) -> dict[str, str]:
        assert access_token == "access-token"
        assert user_id == USER_ID
        assert title == expected_title
        return thread_row(title=title)

    monkeypatch.setattr(chat, "create_thread", fake_create_thread)

    response = (
        client.post("/chat/threads", json=body)
        if body
        else client.post("/chat/threads")
    )

    assert response.status_code == 201
    assert response.json()["title"] == expected_title


def test_load_message_history(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def fake_owner(thread_id: UUID) -> UUID:
        assert thread_id == THREAD_ID
        return USER_ID

    async def fake_messages(
        access_token: str, thread_id: UUID
    ) -> list[dict[str, object]]:
        assert access_token == "access-token"
        assert thread_id == THREAD_ID
        return [
            {
                "id": str(uuid4()),
                "role": "assistant",
                "parts": [{"type": "text", "text": "Saved reply"}],
            }
        ]

    monkeypatch.setattr(chat, "get_thread_owner", fake_owner)
    monkeypatch.setattr(chat, "load_messages", fake_messages)

    response = client.get(f"/chat/threads/{THREAD_ID}/messages")

    assert response.status_code == 200
    assert response.json()[0]["parts"] == [{"type": "text", "text": "Saved reply"}]


@pytest.mark.parametrize(
    ("owner", "expected_status"),
    [(None, 404), (OTHER_USER_ID, 403)],
)
def test_thread_access_errors(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    owner: UUID | None,
    expected_status: int,
) -> None:
    async def fake_owner(thread_id: UUID) -> UUID | None:
        return owner

    monkeypatch.setattr(chat, "get_thread_owner", fake_owner)

    history_response = client.get(f"/chat/threads/{THREAD_ID}/messages")
    stream_response = client.post("/chat/stream", json=stream_body())

    assert history_response.status_code == expected_status
    assert stream_response.status_code == expected_status


def test_streams_and_persists_completed_turn(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    persisted: dict[str, object] = {}

    async def fake_owner(thread_id: UUID) -> UUID:
        return USER_ID

    async def fake_append(*args: object) -> None:
        persisted["args"] = args

    monkeypatch.setattr(chat, "get_thread_owner", fake_owner)
    monkeypatch.setattr(chat, "append_chat_turn", fake_append)

    response = client.post("/chat/stream", json=stream_body())
    events = parse_events(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert [event["type"] for event in events[:-1] if isinstance(event, dict)][0:3] == [
        "start",
        "start-step",
        "text-start",
    ]
    deltas = [
        event["delta"]
        for event in events
        if isinstance(event, dict) and event["type"] == "text-delta"
    ]
    assert "".join(deltas) == TEST_REPLY
    assert events[-3:] == [{"type": "finish-step"}, {"type": "finish"}, "[DONE]"]

    args = persisted["args"]
    assert args[0:2] == ("access-token", THREAD_ID)
    assert isinstance(args[2], UUID)
    assert args[3] == "What changed?"
    assert isinstance(args[5], UUID)
    assert args[2] != args[5]
    assert args[6] == TEST_REPLY
    assert args[8] == []
    assert events[0]["messageId"] == str(args[5])


@pytest.mark.parametrize(
    "body",
    [
        {**stream_body(), "trigger": "regenerate-message"},
        {**stream_body(), "messages": []},
        {
            **stream_body(),
            "messages": [
                {
                    "id": "assistant-message",
                    "role": "assistant",
                    "parts": [{"type": "text", "text": "Not a user turn"}],
                }
            ],
        },
        {
            **stream_body(),
            "messages": [
                {
                    "id": "empty-message",
                    "role": "user",
                    "parts": [{"type": "text", "text": "   "}],
                }
            ],
        },
    ],
)
def test_rejects_invalid_stream_requests(
    client: TestClient, body: dict[str, object]
) -> None:
    response = client.post("/chat/stream", json=body)

    assert response.status_code == 422
