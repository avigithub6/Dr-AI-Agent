from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.utils.logger import logger


async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unhandled exception | type=%s",
        type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Something went wrong.",
            "data": None,
        },
    )


async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.error(
        "Database operation failed | type=%s",
        type(exc).__name__,
    )

    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": (
                    "Patient data conflicts with "
                    "database constraints."
                ),
                "data": None,
            },
        )

    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "message": (
                "Database operation could not be completed."
            ),
            "data": None,
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = [
        {
            "location": list(error["loc"]),
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Invalid request.",
            "data": errors,
        },
    )