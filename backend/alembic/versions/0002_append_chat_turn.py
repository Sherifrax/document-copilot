"""Add an atomic chat-turn persistence function.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION public.append_chat_turn(
            p_thread_id uuid,
            p_user_message_id uuid,
            p_assistant_message_id uuid,
            p_user_content text,
            p_user_parts jsonb,
            p_assistant_content text,
            p_assistant_parts jsonb
        )
        RETURNS void
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = public
        AS $$
        DECLARE
            next_message_index integer;
        BEGIN
            PERFORM 1
            FROM public.chat_threads
            WHERE id = p_thread_id
              AND user_id = (SELECT auth.uid())
            FOR UPDATE;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Chat thread not found or forbidden'
                    USING ERRCODE = '42501';
            END IF;

            SELECT COALESCE(MAX(message_index), -1) + 1
            INTO next_message_index
            FROM public.chat_messages
            WHERE thread_id = p_thread_id;

            INSERT INTO public.chat_messages (
                id,
                thread_id,
                message_index,
                role,
                content,
                parts
            )
            VALUES
                (
                    p_user_message_id,
                    p_thread_id,
                    next_message_index,
                    'user',
                    p_user_content,
                    p_user_parts
                ),
                (
                    p_assistant_message_id,
                    p_thread_id,
                    next_message_index + 1,
                    'assistant',
                    p_assistant_content,
                    p_assistant_parts
                );

            UPDATE public.chat_threads
            SET updated_at = now()
            WHERE id = p_thread_id;
        END;
        $$
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION public.append_chat_turn(
            uuid, uuid, uuid, text, jsonb, text, jsonb
        ) FROM PUBLIC, anon
        """
    )
    op.execute(
        """
        GRANT EXECUTE ON FUNCTION public.append_chat_turn(
            uuid, uuid, uuid, text, jsonb, text, jsonb
        ) TO authenticated, service_role
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION public.append_chat_turn(
            uuid, uuid, uuid, text, jsonb, text, jsonb
        )
        """
    )
