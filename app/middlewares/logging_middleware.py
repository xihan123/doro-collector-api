import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.time()
        path = request.url.path
        method = request.method

        logger.info(f"开始请求 [{request_id}] {method} {path}")

        try:
            response = await call_next(request)

            # 记录请求结束
            process_time = time.time() - start_time
            status_code = response.status_code
            logger.info(
                f"完成请求 [{request_id}] {method} {path} - {status_code} - 耗时: {process_time:.3f}s"
            )

            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"请求异常 [{request_id}] {method} {path} - 耗时: {process_time:.3f}s - 错误: {str(e)}"
            )
            raise
