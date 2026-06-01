import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.logging import setup_logging
from core.config import get_settings
from app.infrastructure.storage.redis import get_redis
from app.infrastructure.storage.postgres import get_postgres
from app.interfaces.endpoints.routes import api_router
from app.interfaces.errors.exception_handler import register_exception_handler


# 1.加载配置信息
settings = get_settings()

# 2.设置日志管理器
setup_logging()
logger = logging.getLogger()

# 3.定义 FastAPI 路由 tags 标签
openapi_tags = [
    {
        "name": "状态模块",
        "description": "包含 状态监测 等 API 接口,用于监控系统运行状态",
    }
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    创建 FastAPI 应用程序生命周期上下文管理
    """
    logger.info("nano-manus is initializing...")

    # 初始化 redis 客户端
    redis = get_redis()
    await redis.init()

    # 初始化 postgres 客户端
    postgres = get_postgres()
    await postgres.init()
    
    # todo 
    try:
        # lifespan 节点/分界
        yield
    finally:
        await redis.shutdown()
        await postgres.shutdown()
        logger.info("nano-manus is shutting down...")

app = FastAPI(
    title="nano-manus通用智能体",
    description="nano-manus 是一个通用智能体系统,可以完全私有部署,使用 A2A+MCP连接 Agent/Tools,同时支持在沙箱环境中运行",
    lifespan=lifespan,
    version="0.1.0",
    tags=openapi_tags,
)

# 5.配置 CORS 中间件,解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6.集成异常处理器
register_exception_handler(app)

# 7.集成路由
app.include_router(api_router, prefix="/api")