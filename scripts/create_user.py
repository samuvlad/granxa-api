"""Crear un usuario no sistema.

Uso dende a raíz do proxecto:

    python scripts/create_user.py <username> <password> [email]

Dentro do contedor Docker:

    docker compose exec api python scripts/create_user.py <username> <password> [email]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models import User


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print(
            "Uso: python scripts/create_user.py <username> <password> [email]",
            file=sys.stderr,
        )
        sys.exit(1)
    username, password = sys.argv[1], sys.argv[2]
    email = sys.argv[3] if len(sys.argv) == 4 else None
    if not username.strip():
        print("O username non pode estar baleiro", file=sys.stderr)
        sys.exit(1)
    if len(password) < 6:
        print(
            "O password debe ter polo menos 6 caracteres", file=sys.stderr
        )
        sys.exit(1)

    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.username == username)
        ).first()
        if existing is not None:
            print(f"Xa existe o usuario '{username}'", file=sys.stderr)
            sys.exit(1)
        if email is not None:
            existing_email = session.exec(
                select(User).where(User.email == email)
            ).first()
            if existing_email is not None:
                print(
                    f"Xa existe un usuario con email '{email}'",
                    file=sys.stderr,
                )
                sys.exit(1)

        user = User(
            username=username,
            email=email,
            hashed_password=bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
        )
        session.add(user)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            print(f"Erro ao crear o usuario: {exc}", file=sys.stderr)
            sys.exit(1)
        session.refresh(user)
        print(
            f"Usuario '{user.username}' creado con id={user.id} "
            f"email={user.email!r} "
            f"(DB: {settings.database_url.rsplit('/', 1)[-1]})"
        )


if __name__ == "__main__":
    main()
