import logging
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import AppConfigService
from app.application.services.status_service import StatusService
from app.infrastructure.external.health_checker.postgres_health_checker import PostgresHealthChecker
from app.infrastructure.external.health_checker.redis_health_checker import RedisHealthChecker
from app.infrastructure.repository import FileAppConfigRepository
from core.config import Settings, get_settings
from app.infrastructure.storage.postgres import get_db_session
from app.infrastructure.storage.redis import RedisClient, get_redis

logger = logging.getLogger(__name__)
settings: Settings = get_settings()

@lru_cache()
def get_app_config_service() -> AppConfigService:
    """获取应用配置服务"""
    # 1.获取数据仓储层实现并打印日志
    logger.info("加载获取 AppConfigService")
    file_app_config_repo = FileAppConfigRepository(settings.app_config_filepath)

    # 2.实例化 AppConfigService
    app_config_service = AppConfigService(app_config_repo=file_app_config_repo)

    return app_config_service

@lru_cache()
def get_status_service(
    db_session: AsyncSession = Depends(get_db_session),
    redis_client: RedisClient = Depends(get_redis)
) -> StatusService:
    """获取状态检测服务"""
    # 1.初始化 postgres/redis 状态检查服务
    postgres_checker = PostgresHealthChecker(db_session)
    redis_checker = RedisHealthChecker(redis_client)

    logger.info("初始化并获取 StatusService")
    return StatusService(checkers=[postgres_checker, redis_checker])
    