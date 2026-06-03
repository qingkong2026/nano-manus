import logging
from functools import lru_cache

from redis.asyncio import Redis

from core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis 客户端，用于完成 redis 缓存连接&使用
    """

    def __init__(self) -> None:
        self._client: Redis | None = None
        self._setting: Settings = get_settings()

    async def init(self) -> None:
        """
        完成 redis 客户端的初始化
        """
        # 1.判断客户端是否已经初始化
        if self._client:
            logger.warning("RedisClient is already initialized")
            return
        # 2.尝试初始化 redis
        try:
            # 2.1 创建 redis 客户端
            self._client = Redis(
                host=self._setting.redis_host,
                port=self._setting.redis_port,
                db=self._setting.redis_db,
                password=self._setting.redis_password,
                protocol=2,
            )
            # 2.2 测试连接
            await self._client.ping()
            logger.info("RedisClient initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize RedisClient", exc_info=e)
            raise

    async def shutdown(self) -> None:
        """
        关闭 redis 客户端
        """
        if self._client is not None:
            await self._client.aclose()
            logger.info("RedisClient shutdown successfully")
            # 清除缓存
            get_redis.cache_clear()

    @property
    def client(self) -> Redis | None:
        """
        获取 redis 客户端
        """
        if self._client is None:
            raise RuntimeError("RedisClient is not initialized, please call init first")
        return self._client


@lru_cache()
def get_redis() -> RedisClient:
    """
    获取 redis 客户端
    """
    return RedisClient()
