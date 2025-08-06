"""Custom middleware for error handling and logging."""

import time
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling and logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            # Log incoming request
            logger.info(f"📥 {request.method} {request.url.path}")
            
            response = await call_next(request)
            
            # Log response time
            process_time = time.time() - start_time
            logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            
            return response
            
        except Exception as exc:
            # Log the full error with traceback
            process_time = time.time() - start_time
            error_id = f"ERR_{int(time.time())}"
            
            logger.error(f"❌ Unhandled error [{error_id}] in {request.method} {request.url.path}:")
            logger.error(f"Error: {str(exc)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.error(f"Process time: {process_time:.3f}s")
            
            # Return a clean error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error (ID: {error_id})",
                    "error_type": type(exc).__name__,
                    "timestamp": int(time.time())
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log request details (excluding sensitive data)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.debug(f"🔍 Request details - IP: {client_ip}, User-Agent: {user_agent[:50]}...")
        
        # Log request body size for file uploads
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            content_length = request.headers.get("content-length", "unknown")
            logger.info(f"📁 File upload - Content-Length: {content_length} bytes")
        
        response = await call_next(request)
        
        # Log response details
        logger.debug(f"📋 Response - Status: {response.status_code}, Headers: {dict(response.headers)}")
        
        return response