import logging
from functools import lru_cache

from app.application.services import AppConfigService
from app.infrastructure.repository import FileAppConfigRepository
from core.config import Settings, get_settings

logger = logging.getLogger(__name__)
settings: Settings = get_settings()

@lru_cache
def get_app_config_service() -> AppConfigService:
    """获取应用配置服务"""
    # 1.获取数据仓储层实现并打印日志
    logger.info("加载获取 AppConfigService")
    file_app_config_repo = FileAppConfigRepository(settings.app_config_filepath)

    # 2.实例化 AppConfigService
    app_config_service = AppConfigService(app_config_repo=file_app_config_repo)

    return app_config_service
