import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time=time.time()
        logger.info(f"Incoming Request | {request.method} {request.url.path}")
        response = await call_next(request)
        process_time=round(time.time() - start_time, 4)
        logger.info(
            f"Completed Request | {request.method} {request.url.path} | "
            f"Status: {response.status_code} | Time: {process_time}s"
        )
        response.headers["X-Process-Time"] = str(process_time)
        return response