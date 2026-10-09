from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db


router = APIRouter(tags=["Health"])


@router.get("/")
def root():
    return {
        "message": "Welcome to Dr AI Agent"
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@router.get("/health/db")
def database_health(
    db: Annotated[Session, Depends(get_db)],
):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }