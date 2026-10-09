from alembic import op
import sqlalchemy as sa


revision = "0002_create_conversations"
down_revision = "0001_create_patients"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column(
            "session_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
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
            ["patient_id"],
            ["patients.id"],
            name="fk_conversations_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "session_id",
            name="pk_conversations",
        ),
    )

    op.create_index(
        "ix_conversations_patient_updated_at",
        "conversations",
        ["patient_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_chat_messages_role_values",
        ),
        sa.CheckConstraint(
            "char_length(trim(content)) > 0",
            name="ck_chat_messages_content_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["conversations.session_id"],
            name="fk_chat_messages_session_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_chat_messages",
        ),
    )

    op.create_index(
        "ix_chat_messages_session_created_at_id",
        "chat_messages",
        ["session_id", "created_at", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_chat_messages_session_created_at_id",
        table_name="chat_messages",
    )
    op.drop_table("chat_messages")

    op.drop_index(
        "ix_conversations_patient_updated_at",
        table_name="conversations",
    )
    op.drop_table("conversations")