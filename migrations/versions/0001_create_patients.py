from alembic import op
import sqlalchemy as sa


revision = "0001_create_patients"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patients",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "full_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "age",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "gender",
            sa.String(length=20),
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
        sa.CheckConstraint(
            "age >= 0 AND age <= 130",
            name="ck_patients_age_range",
        ),
        sa.CheckConstraint(
            "gender IN "
            "('male', 'female', 'other', 'prefer_not_to_say')",
            name="ck_patients_gender_values",
        ),
        sa.CheckConstraint(
            "char_length(trim(full_name)) BETWEEN 2 AND 100",
            name="ck_patients_full_name_length",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_patients",
        ),
    )

    op.create_index(
        "ix_patients_full_name",
        "patients",
        ["full_name"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_patients_full_name",
        table_name="patients",
    )

    op.drop_table("patients")