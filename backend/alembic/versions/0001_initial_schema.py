"""Initial application schema, retrieval indexes, and ownership policies.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path TO public, extensions")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("cik", sa.Text(), nullable=False),
        sa.Column("filing_type", sa.Text(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_documents")),
        sa.UniqueConstraint(
            "accession_number", name=op.f("uq_source_documents_accession_number")
        ),
    )
    op.create_index(
        op.f("ix_source_documents_ticker"), "source_documents", ["ticker"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["auth.users.id"],
            name=op.f("fk_users_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "chat_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_threads_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_threads")),
    )
    op.create_index(
        op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, content)", persisted=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0", name=op.f("ck_document_chunks_chunk_index_nonnegative")
        ),
        sa.CheckConstraint(
            "token_count >= 0", name=op.f("ck_document_chunks_token_count_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["source_documents.id"],
            name=op.f("fk_document_chunks_document_id_source_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name=op.f("uq_document_chunks_document_id")
        ),
    )
    op.create_index(
        "ix_document_chunks_embedding",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("message_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name=op.f("ck_chat_messages_role_valid")
        ),
        sa.CheckConstraint(
            "message_index >= 0",
            name=op.f("ck_chat_messages_message_index_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            name=op.f("fk_chat_messages_thread_id_chat_threads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
        sa.UniqueConstraint(
            "thread_id", "message_index", name=op.f("uq_chat_messages_thread_id")
        ),
    )
    op.create_table(
        "message_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "citation_index > 0",
            name=op.f("ck_message_citations_citation_index_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            name=op.f("fk_message_citations_chunk_id_document_chunks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name=op.f("fk_message_citations_message_id_chat_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_citations")),
        sa.UniqueConstraint(
            "message_id", "citation_index", name=op.f("uq_message_citations_message_id")
        ),
    )
    op.create_index(
        op.f("ix_message_citations_chunk_id"),
        "message_citations",
        ["chunk_id"],
        unique=False,
    )

    op.execute("ALTER TABLE public.source_documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON TABLE public.source_documents FROM PUBLIC, anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.source_documents TO service_role"
    )
    op.execute("GRANT SELECT ON TABLE public.source_documents TO authenticated")
    op.execute(
        "CREATE POLICY source_documents_read ON public.source_documents FOR SELECT TO authenticated USING (true)"
    )
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE public.users FROM PUBLIC, anon, authenticated")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users TO service_role"
    )
    op.execute("GRANT SELECT ON TABLE public.users TO authenticated")
    op.execute(
        "CREATE POLICY users_owner ON public.users FOR SELECT TO authenticated USING (id = (SELECT auth.uid()))"
    )
    op.execute("ALTER TABLE public.chat_threads ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON TABLE public.chat_threads FROM PUBLIC, anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.chat_threads TO service_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.chat_threads TO authenticated"
    )
    op.execute(
        "CREATE POLICY chat_threads_owner ON public.chat_threads FOR ALL TO authenticated USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()))"
    )
    op.execute("ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON TABLE public.document_chunks FROM PUBLIC, anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.document_chunks TO service_role"
    )
    op.execute("GRANT SELECT ON TABLE public.document_chunks TO authenticated")
    op.execute(
        "CREATE POLICY document_chunks_read ON public.document_chunks FOR SELECT TO authenticated USING (true)"
    )
    op.execute("ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON TABLE public.chat_messages FROM PUBLIC, anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.chat_messages TO service_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.chat_messages TO authenticated"
    )
    op.execute(
        "CREATE POLICY chat_messages_owner ON public.chat_messages FOR ALL TO authenticated USING (EXISTS (SELECT 1 FROM public.chat_threads t WHERE t.id = chat_messages.thread_id AND t.user_id = (SELECT auth.uid()))) WITH CHECK (EXISTS (SELECT 1 FROM public.chat_threads t WHERE t.id = chat_messages.thread_id AND t.user_id = (SELECT auth.uid())))"
    )
    op.execute("ALTER TABLE public.message_citations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE ALL ON TABLE public.message_citations FROM PUBLIC, anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.message_citations TO service_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.message_citations TO authenticated"
    )
    op.execute(
        "CREATE POLICY message_citations_owner ON public.message_citations FOR ALL TO authenticated USING (EXISTS (SELECT 1 FROM public.chat_messages m JOIN public.chat_threads t ON t.id = m.thread_id WHERE m.id = message_citations.message_id AND t.user_id = (SELECT auth.uid()))) WITH CHECK (EXISTS (SELECT 1 FROM public.chat_messages m JOIN public.chat_threads t ON t.id = m.thread_id WHERE m.id = message_citations.message_id AND t.user_id = (SELECT auth.uid())))"
    )


def downgrade() -> None:
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("document_chunks")
    op.drop_table("chat_threads")
    op.drop_table("users")
    op.drop_table("source_documents")
    # The extension may be shared by other schemas; leave it installed.
