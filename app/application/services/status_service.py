import asyncio
import time
from typing import List

from app.domain.models.health_status import HealthStatus
from app.domain.external.health_checker import HealthChecker

class StatusService:
    """状态检查服务，用于检查系统的依赖服务状态"""

    def __init__(self, checkers: List[HealthChecker]) -> None:
        self._checkers = checkers

    async def check_all(self) -> List[HealthStatus]:
        """检查所有健康检查器的状态"""
        tasks = [checker.check() for checker in self._checkers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result,Exception):
                processed_results.append({
                    "service": "未知服务",
                    "status": "error",
                    "timestamp": int(time.time()),
                    "details": f"未知检查器发生异常：{str(result)}",
                })
            else:
                processed_results.append(result)
        return processed_results
