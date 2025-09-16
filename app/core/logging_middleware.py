import logging
from fastapi import Request

logger = logging.getLogger("afe_backend")

async def log_requests(request: Request, call_next):
    logger.info("Petición: %s %s", request.method, request.url)
    response = await call_next(request)
    logger.info("Respuesta: %s %s", response.status_code, request.url)
    return response
