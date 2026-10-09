import hmac
import logging
from typing import Annotated

from datetime import datetime, timezone

from app.database.models.refresh_token import RefreshToken

from app.core.security import (
    create_refresh_token,
    hash_refresh_token,
)

from app.models.auth import (
    RefreshRequest,
    LogoutRequest,
)

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    AdminUser,
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from app.database.models.user import User
from app.database.session import get_db
from app.models.auth import (
    BootstrapRequest,
    ClinicianCreate,
    TokenResponse,
    UserResponse,
)


logger = logging.getLogger("Dr AI Agent")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/bootstrap",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_first_admin(
    data: BootstrapRequest,
    db: Annotated[Session, Depends(get_db)],
    bootstrap_token: Annotated[str, Header(alias="X-Bootstrap-Token")],
):
    expected_token = settings.AUTH_BOOTSTRAP_TOKEN.get_secret_value()

    if not hmac.compare_digest(bootstrap_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bootstrap token.",
        )

    try:
        # PostgreSQL transaction lock makes first-admin creation one-time,
        # including when two bootstrap requests arrive at the same time.
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": 7351902841},
        )

        user_count = db.scalar(
            select(func.count()).select_from(User)
        )

        if user_count:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admin bootstrap has already been completed.",
            )

        admin = User(
            email=str(data.email).strip().lower(),
            password_hash=hash_password(data.password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info("Initial admin account created | user_id=%s", admin.id)
        return admin

    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    except Exception:
        db.rollback()
        logger.exception("Admin bootstrap failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the initial admin account.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    email = form_data.username.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None or not user.is_active:
        # Run the password verifier for unknown users too, to reduce
        # response-time differences between unknown email and wrong password.
        verify_password(
            form_data.password,
            hash_password("fixed-dummy-password-for-login-timing"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_in = create_access_token(user.id)
    refresh_token, token_hash, expires_at = create_refresh_token()

    session = RefreshToken(
    user_id=user.id,
    token_hash=token_hash,
    expires_at=expires_at,
    )

    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_account(current_user: CurrentUser):
    return current_user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_clinician(
    data: ClinicianCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: AdminUser,
):
    clinician = User(
        email=str(data.email).strip().lower(),
        password_hash=hash_password(data.password),
        role="clinician",
        is_active=True,
    )

    db.add(clinician)

    try:
        db.commit()
        db.refresh(clinician)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    logger.info(
        "Clinician account created | admin_id=%s clinician_id=%s",
        admin.id,
        clinician.id,
    )
    return clinician

@router.post("/refresh", response_model=TokenResponse)
def refresh_session(
    data: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
):
    now = datetime.now(timezone.utc)

    token_hash = hash_refresh_token(data.refresh_token)

    # Row lock prevents concurrent requests from rotating
    # the same refresh token successfully.
    session = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )

    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = db.scalar(
        select(User).where(
            User.id == session.user_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or unavailable.",
        )

    # Revoke old token.
    session.revoked_at = now

    # Create replacement refresh token.
    new_refresh_token, new_hash, expires_at = (
        create_refresh_token()
    )

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=expires_at,
        )
    )

    access_token, expires_in = create_access_token(user.id)

    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
    )


@router.post("/logout")
def logout_session(
    data: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
):
    token_hash = hash_refresh_token(data.refresh_token)

    session = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )

    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
    else:
        db.rollback()

    return {"message": "Session logged out."}