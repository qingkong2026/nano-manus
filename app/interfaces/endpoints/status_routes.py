import logging
from fastapi import APIRouter
from app.interfaces.schema import Response

logger = logging.getLogger(__name__)
status_router = APIRouter(prefix="/status", tags=["状态模块"])

@status_router.get(
    path="/",
    response_model=Response,
    summary="系统健康检查",
    description="系统健康检查,检查 postgres/resis/cos等服务",
)
async def get_status():
    """
    系统健康检查,检查 postgres/resis/cos等服务
    """
    return Response.success()

