import logging
import re
from functools import lru_cache
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

logger = logging.getLogger(__name__)


class Postgres:
    """
    Postgres 数据库基础类，用于完成数据库连接等配置操作
    """

    def __init__(self) -> None:
        """
        构造函数，完成 Postgres 数据库引擎，会话工厂的初始化
        """
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._settings = get_settings()

    async def init(self) -> None:
        """
        初始化 postgres 连接
        """
        # 1.判断是否已经创建好引擎
        if self._engine is not None:
            logger.warning("Postgres engine had already initialized")
            return

        try:
            # 2.创建数据库引擎
            logger.info("Initializing Postgres connection ...")
            self._engine = create_async_engine(
                self._settings.sqlalchemy_database_url,
                echo=True if self._settings.env == "development" else False,
            )

            # 3.创建会话工厂
            self._session_factory = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
            )
            logger.info("Postgres session_factory initialized successfully")

            # 4.连接 postgres 并执行预操作
            async with self._engine.begin() as async_conn:
                # 5.检查是否安装了 uuid 扩展
                await async_conn.execute(
                    text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
                )
                logger.info(
                    "Postgres engine initialized successfully and uuid-ossp extension installed"
                )
        except Exception as e:
            logger.error(f"Failed to initialize Postgres engine: {e}")
            raise

    async def shutdown(self) -> None:
        """
        关闭 Postgres 连接
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Postgres connection closed successfully")
            get_postgres.cache_clear()

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        只读属性，返回已初始化的会话工厂
        """
        if self._session_factory is None:
            raise RuntimeError(
                "session_factory is not initialized, please call init() first"
            )
        return self._session_factory


@lru_cache()
def get_postgres() -> Postgres:
    """
    单例模式获取 Postgres 实例
    """
    return Postgres()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    异步获取数据库会话实例，确保会话在正确使用后被关闭
    """
    # 1. 获取 Postgres 实例和会话工厂
    db = get_postgres()
    session_factory = db.session_factory

    # 2.创建会话上下文，在上下文内完成数据提交
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as _:
            await session.rollback()
            raise
