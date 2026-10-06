# Phase 8 pilot readiness

This is the focused acceptance checklist for five senior analysts over one
week. It intentionally separates retrieval, product persistence, and operating
checks instead of treating one large end-to-end run as proof.

## Ten-question smoke test

1. Run `uv run python scripts/evaluate_retrieval.py` from `backend/`.
2. Confirm all ten labeled probes print results. A probe is a failure if it
   returns no passages, wrong ticker scope, missing page/section metadata, or
   passages that do not support the requested comparison.
3. In the browser, ask the exact ten questions in the client brief. For each,
   save one answer screenshot/link and mark: sourced, page-visible, passage
   visible, and grounded/refused when evidence is insufficient.

The retrieval script is a preflight, not a claim that the LLM answer is correct.
The browser pass verifies citations, grounding, and the user experience.

## Persistence across sessions

With an authenticated pilot account:

1. Create a thread, ask one question, and wait for the completed answer.
2. Refresh the page and confirm the thread remains in the sidebar.
3. Open the thread in a new browser tab or after signing out and back in.
4. Confirm both the user question and assistant answer, including citations,
   are present. Repeat with a second account and confirm it cannot open the
   first account's thread.

The API path under test is `GET /chat/threads` plus
`GET /chat/threads/{thread_id}/messages`; completed turns are saved atomically
by the `append_chat_turn` RPC.

## Scale and latency checks

- Confirm the database schema and API calls always scope threads/messages by
  authenticated user and thread owner; no client-side single-user state is the
  source of truth.
- Have five analysts use separate accounts concurrently for a short burst of
  questions. Watch structured logs for `request_finished`, `chat_turn_failed`,
  and `stream_generation_failed`; no access token or document text should appear.
- For ten ordinary questions, record time to first `text-delta`. Target: the
  stream starts within a few seconds for typical queries. Also record total
  completion time and any persistence failures.
- Before firm-wide rollout, repeat with a load shape representative of roughly
  40 analysts and review Postgres connection limits, OpenAI rate limits, and
  retrieval p95. The current code has no single-user cache or in-memory chat
  history, but this is an operational capacity check, not a proof of capacity.

## Pilot outcome

Each analyst logs intake time saved per week and one groundedness issue or
successful example. The pilot passes when the five-analyst group reports at
least three hours saved per analyst per week and no unresolved citation or
cross-user data-isolation defect.
