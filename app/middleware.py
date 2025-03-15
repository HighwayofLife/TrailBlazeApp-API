import time
from typing import Callable
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_logger

logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses with timing info."""
    
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state for logging context
        request.state.request_id = request_id
        
        # Log the request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "path": request.url.path,
            },
        )
        
        # Process the request and get response
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "processing_time_ms": round(process_time * 1000, 2),
                },
            )
            
            # Add custom headers to track performance
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log exceptions
            process_time = time.time() - start_time
            logger.exception(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "processing_time_ms": round(process_time * 1000, 2),
                    "error": str(e),
                },
            )
            raise
