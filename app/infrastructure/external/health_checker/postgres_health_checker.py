import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.external.health_checker import HealthChecker
from app.domain.models.health_status import HealthStatus

logger = logging.getLogger(__name__)

class PostgresHealthChecker(HealthChecker):
    """postgres 数据库健康检查器"""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def check(self) -> HealthStatus:
        try:
            await self._db_session.execute(text("SELECT 1"))
            return HealthStatus(
                service="postgres",
                status="ok",
                timestamp=int(time.time()),
                details="",
            )
        except Exception as e:
            logger.error(f"Postgres 数据库健康检查失败: str{e}")
            return HealthStatus(
                service="postgres",
                status="error",
                timestamp=int(time.time()),
                details=str(e),
            )