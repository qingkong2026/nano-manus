from typing import Protocol

from app.domain.models.health_status import HealthStatus

class HealthChecker(Protocol):
    """健康检查器协议，定义了健康检查的接口"""

    async def check(self) -> HealthStatus:
        """检查服务是否健康"""
        ...
    
        