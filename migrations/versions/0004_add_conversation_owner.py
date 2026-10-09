"""Add authenticated user ownership to conversations."""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_conversation_owner"
down_revision = "0003_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    existing_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM conversations")
    ).scalar_one()

    if existing_count:
        raise RuntimeError(
            "Existing conversations require an explicit owner "
            "backfill before this migration can run."
        )

    op.add_column(
        "conversations",
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            nullable=False,
        ),
    )

    op.create_foreign_key(
        "fk_conversations_owner_user_id_users",
        "conversations",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_conversations_owner_user_id",
        "conversations",
        ["owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversations_owner_user_id",
        table_name="conversations",
    )

    op.drop_constraint(
        "fk_conversations_owner_user_id_users",
        "conversations",
        type_="foreignkey",
    )

    op.drop_column(
        "conversations",
        "owner_user_id",
    )