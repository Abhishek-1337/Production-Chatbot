"""add conversations and connect messages to them

Revision ID: 8f2a1c4d9b7e
Revises: 46535509e1a9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2a1c4d9b7e"
down_revision: Union[str, Sequence[str], None] = "46535509e1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("name", sa.String(length=255), nullable=True))
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_document_id", "conversations", ["document_id"])
    op.add_column("chat_messages", sa.Column("conversation_id", sa.UUID(), nullable=True))
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_foreign_key(
        "fk_chat_messages_conversation_id", "chat_messages", "conversations", ["conversation_id"], ["id"]
    )
    op.drop_constraint("chat_messages_user_id_fkey", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "user_id")


def downgrade() -> None:
    op.add_column("chat_messages", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key("chat_messages_user_id_fkey", "chat_messages", "users", ["user_id"], ["id"])
    op.drop_constraint("fk_chat_messages_conversation_id", "chat_messages", type_="foreignkey")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_column("chat_messages", "conversation_id")
    op.drop_index("ix_conversations_document_id", table_name="conversations")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_column("documents", "name")
