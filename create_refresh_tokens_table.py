from app.database.base import Base
from app.database.session import engine

from app.database.models.user import User
from app.database.models.refresh_token import RefreshToken


def main():
    RefreshToken.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print("Refresh token table is ready.")


if __name__ == "__main__":
    main()