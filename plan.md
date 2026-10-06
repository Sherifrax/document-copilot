# Phase 6 — LLM Agent and Grounding

## Goal

Turn the verified Phase 5 retrieval pipeline into a PydanticAI-powered assistant
that answers only from retrieved SEC filing passages, validates every citation,
streams the validated result, and persists the complete chat turn atomically.

## 1. Agent contracts and configuration

- Add a required `OPENAI_CHAT_MODEL` setting and document it in the backend
  environment example.
- Define `DocumentAgentDeps` with the authenticated user ID, thread ID,
  `DocumentRetriever`, `GroundingValidator`, and a request-scoped evidence
  registry.
- Define typed Pydantic models for `GroundedAnswer`, citations, and the validated
  cited passages returned to the chat layer.
- Keep retrieval and grounding independent from PydanticAI so they remain usable
  and testable without an LLM call.

## 2. Bounded PydanticAI tools

- Implement `search_filings` using the existing hybrid retriever and its ticker,
  filing-type, and fiscal-year filters.
- Implement `read_chunk` for loading one passage by its stable chunk ID.
- Implement `read_surrounding_chunks` for expanding a selected passage with
  neighboring chunks from the same filing.
- Register every passage returned by a tool in the request-scoped evidence
  registry. The model may cite only passages in this registry.
- Do not expose SQL, unrestricted database access, or arbitrary filters to the
  model.
- Configure explicit request, token, retry, and tool-call limits.
- Instruct the agent to decompose comparative questions into filtered
  per-company or per-year searches. Phase 5 evaluation showed that a single
  broad search can be dominated by the strongest-matching company.

## 3. Agent instructions and grounding policy

- Answer only from retrieved SEC filing passages.
- Require inline citation markers for factual paragraphs.
- State that the corpus lacks sufficient evidence when the tools do not return
  adequate support.
- Prohibit stock recommendations, investment advice, and causal conclusions not
  stated in the filings.
- Keep answers concise enough for analyst review while preserving the evidence
  needed to verify each claim.
- Add a grounding validator that confirms:
  - every citation references a passage retrieved during the current run;
  - every cited excerpt occurs in the referenced chunk after whitespace
    normalization;
  - citation markers are valid, ordered, and resolve to citation records;
  - factual answer paragraphs contain citations;
  - insufficient-evidence responses do not introduce unsupported facts.
- Use a PydanticAI output validator to request one corrected answer after a
  validation failure. If the correction also fails, return a controlled
  insufficient-evidence response and do not persist an ungrounded answer.

## 4. Chat orchestration and streaming

- Add `chat/orchestrator.py` to coordinate one authenticated turn:
  1. Load the stored conversation history.
  2. Create request-scoped dependencies and evidence storage.
  3. Run the PydanticAI agent.
  4. Validate the structured answer and citations.
  5. Convert the validated result into chat text and citation metadata.
  6. Persist the complete turn.
- Replace the stub reply in the chat streaming route with the orchestrator.
- Buffer model output until grounding validation succeeds, then emit AI
  SDK-compatible text deltas and citation metadata. This prevents unvalidated
  claims from reaching the browser.
- Emit controlled error events for agent, retrieval, grounding, and persistence
  failures without exposing credentials or internal exception details.
- Leave citation-chip and source-passage rendering to Phase 7.

## 5. Atomic persistence

- Extend the existing `append_chat_turn` database function through a reviewed
  Alembic migration so it accepts validated citations.
- Insert the user message, assistant message, and `message_citations` rows in one
  database transaction.
- Validate referenced chunk IDs, preserve citation order, and store the
  validated supporting excerpt.
- Do not leave partial messages behind when agent execution, grounding, or
  persistence fails.

## 6. Tests and acceptance criteria

- Unit-test the three agent tools, filter forwarding, evidence registration,
  and per-company comparative search behavior.
- Unit-test valid citations, missing citation markers, fabricated chunk IDs,
  mismatched excerpts, malformed numbering, retry behavior, and the final
  fail-closed response.
- Test the orchestrator with PydanticAI's test model and mocked retrieval so the
  normal suite makes no OpenAI or Supabase calls.
- Test atomic chat-and-citation persistence and rollback behavior.
- Test the AI SDK stream for text, citation metadata, completion, and controlled
  error events.
- Add guarded integration tests for representative Apple, NVIDIA, and
  cross-company questions.
- Verify before marking Phase 6 complete:
  - every answer citation resolves to a real retrieved chunk;
  - citation records include filing metadata and supporting text;
  - comparative questions search every requested company;
  - unsupported generative-AI margin conclusions are refused;
  - retrieval and grounding failures are not persisted as successful answers;
  - the full non-integration backend test suite and Ruff checks pass.

## Out of scope

- Citation chips, source drawers, and other trust UI work belong to Phase 7.
- Cross-encoder reranking, external sources, agent-generated SQL, and investment
  recommendations are not part of Phase 6.
