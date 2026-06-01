import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


from app.application.errors.exceptions import AppException
from app.interfaces.schema import Response

logger = logging.getLogger(__name__)

def register_exception_handler(app: FastAPI):
    """
    处理项目中所有的异常并进行统一处理，涵盖：自定义业务异常 、HTTP 异常、通用异常
    """

    @app.exception_handler(Exception)
    async def exception_handler(req: Request, e: Exception) -> JSONResponse:
        """
        处理项目中抛出的未定义的任意一一场，将状态码统一设置为 500
        """
        logger.error(f"Exception: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=Response(
                code=500,
                msg="服务器出现异常,请稍后再试",
                data={}
            ).model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(req: Request, e: HTTPException) -> JSONResponse:
        """
        处理FastAPI 抛出的 HTTP 异常，将所有状态统一响应结构
        """
        logger.error(f"HTTPException: {str(e)}")
        return JSONResponse(
            status_code=e.status_code,
            content=Response(
                code=e.status_code,
                msg=e.detail,
                data={}
            ).model_dump()
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(req: Request, e: AppException) -> JSONResponse:
        """
        处理自定义业务异常
        """
        logger.error(f"AppException: {str(e.msg)}")
        return JSONResponse(
            status_code=e.status_code,
            content=Response(
                code=e.status_code,
                msg=e.msg,
                data={}
            ).model_dump()
        )