"""Canal WhatsApp próprio com histórico e estado de entrega."""

import sqlalchemy as sa
from alembic import op

revision = "20261112_whatsapp_channel"
down_revision = "20261112_site_chat"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "site_conversations",
        sa.Column("channel", sa.String(16), server_default="web", nullable=False),
    )
    op.add_column("site_conversations", sa.Column("whatsapp_recipient", sa.Text(), nullable=True))
    op.add_column(
        "site_conversations",
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("site_messages", sa.Column("provider_id", sa.String(192), nullable=True))
    op.add_column("site_messages", sa.Column("delivery", sa.String(16), nullable=True))
    op.create_unique_constraint("uq_site_messages_provider_id", "site_messages", ["provider_id"])


def downgrade():
    op.drop_constraint("uq_site_messages_provider_id", "site_messages", type_="unique")
    op.drop_column("site_messages", "delivery")
    op.drop_column("site_messages", "provider_id")
    op.drop_column("site_conversations", "last_inbound_at")
    op.drop_column("site_conversations", "whatsapp_recipient")
    op.drop_column("site_conversations", "channel")
