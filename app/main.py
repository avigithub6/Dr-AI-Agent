from fastapi import FastAPI
from app.config import settings
from app.api.router import api_router
from app.core.exception_handler import global_exception_handler
from app.core.middleware import RequestLoggingMiddleware
from app.utils.logger import logger

logger.info("Starting Dr AI Agent")

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)

app.add_exception_handler(Exception, global_exception_handler)

logger.info("Application initialized successfully")