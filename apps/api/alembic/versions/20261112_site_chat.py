"""Canal de atendimento do site, sem dependência da Meta."""

from alembic import op
import sqlalchemy as sa

revision = "20261112_site_chat"
down_revision = "911a9f890948"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_conversations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("site_slug", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_site_conversations_site_updated", "site_conversations", ["site_slug", "updated_at"])
    op.create_table(
        "site_messages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("site_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("conversation_id", "client_id", name="uq_site_message_client"),
    )
    op.create_index("ix_site_messages_conversation_created", "site_messages", ["conversation_id", "created_at"])


def downgrade():
    op.drop_table("site_messages")
    op.drop_table("site_conversations")
