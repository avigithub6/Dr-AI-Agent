from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.config import settings
from app.core.exception_handler import (
    database_exception_handler,
    global_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import RequestLoggingMiddleware
from app.database.session import engine
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting Dr AI Agent")

    try:
        yield

    finally:
        engine.dispose()
        logger.info("Dr AI Agent stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


app.add_middleware(
    RequestLoggingMiddleware
)

app.include_router(api_router)


app.add_exception_handler(
    SQLAlchemyError,
    database_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    global_exception_handler,
)


logger.info("Application initialized successfully")