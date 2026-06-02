import logging
from functools import lru_cache
from typing import Optional

from qcloud_cos import CosConfig, CosS3Client

from core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class Cos:
    """
    腾讯云 COS 存储客户端
    """

    def __init__(self) -> None:
        self._settings: Settings = get_settings()
        self._client: Optional[CosS3Client] = None

    async def init(self) -> None:
        """
        初始化 COS 客户端
        """
        # 1.判断是否已经初始化
        if self._client is not None:
            logger.warning("qcloud cos client already initialized")
            return
        try:
            # 2.初始化客户端
            config = CosConfig(
                SecretId=self._settings.cos_secret_id,
                SecretKey=self._settings.cos_secret_key,
                Region=self._settings.cos_region,
                Token=None,
                Scheme=self._settings.cos_schema,
            )
            self._client = CosS3Client(config)
            logger.info("qcloud cos client initialized successfully ...")
        except Exception as e:
            logger.error("failed to initialize qcloud cos client: %s", e)
            raise

    async def shutdown(self) -> None:
        """
        关闭 COS 客户端
        """
        if self._client:
            self._client = None
            logger.info("qcloud cos client shutdown successfully ...")

    @property
    def client(self) -> CosS3Client:
        """
        获取 Cos 客户端
        """
        if self._client is None:
            raise ValueError("qcloud cos client not initialized, please call init() first")
        return self._client

@lru_cache
def get_cos() -> Cos:
    """
    单例模式获取 COS 客户端
    """

    return Cos()
