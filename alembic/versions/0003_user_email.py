"""users.email

Revision ID: 0003_user_email
Revises: 0002_users
Create Date: 2026-06-27 00:00:00.000000

Engade a columna ``email`` (nullable, unique) á táboa ``users``. O
constraint UNIQUE non restrinxe os NULL en PostgreSQL, polo que os
usuarios existentes sen email (ex.: o ``test-user`` do conftest) seguen
sendo válidos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_user_email"
down_revision: Union[str, None] = "0002_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_users_email"), "users", ["email"], unique=True
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
