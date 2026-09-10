import logging
import time

from fastapi import Request

logger = logging.getLogger("liscore.request_time")


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (time.perf_counter() - start_time) * 1000  # ms
    logger.info(
        "%s - \"%s %s\" %s - %.2fms",
        request.client.host if request.client else "-",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )

    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response
