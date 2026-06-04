import logging
from typing import List

from fastapi import APIRouter, Depends

from app.application.services.status_service import StatusService
from app.domain.models.health_status import HealthStatus
from app.interfaces.dependencies import get_status_service
from app.interfaces.schema import Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["状态模块"])


@router.get(
    path="/",
    response_model=Response[List[HealthStatus]],
    summary="系统健康检查",
    description="系统健康检查,检查 postgres/resis/cos等服务",
)
async def get_status(
    status_service: StatusService = Depends(get_status_service),
) -> Response[List[HealthStatus]]:
    """
    系统健康检查,检查 postgres/resis/cos等服务
    """
    status_list = await status_service.check_all()

    if any(item.status == "error" for item in status_list):
        return Response.error(code=503, msg="系统存在服务异常", data=status_list)

    return Response.success(msg="系统健康检查成功", data=status_list)
