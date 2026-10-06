"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.assistant.agent import create_document_agent
from app.chat.orchestrator import ChatOrchestrator
from app.config import settings
from app.database.postgres import create_postgres_engine, create_session_factory
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever


@asynccontextmanager
async def lifespan(application: FastAPI):
    engine = create_postgres_engine(settings.database_url)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    retriever = DocumentRetriever(
        create_session_factory(engine),
        openai_client,
        embedding_model=settings.openai_embedding_model,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    application.state.chat_orchestrator = ChatOrchestrator(
        create_document_agent(settings.openai_chat_model, settings.openai_api_key),
        retriever,
        GroundingValidator(),
    )
    try:
        yield
    finally:
        await openai_client.close()
        await engine.dispose()


app = FastAPI(title="Document Copilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-vercel-ai-ui-message-stream"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API process is accepting requests."""
    return {"status": "ok"}
