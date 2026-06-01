from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    项目后端中控配置信息,从 .env 或者环境变量中加载
    """

    # 项目基础配置
    env: str = "development"
    log_level: str = "INFO"

    # 数据库相关配置
    sqlalchemy_database_url: str = ""

    # Redis 缓存配置
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # 使用 Pydantic V2 写法来完成环境变量信息的告知
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    """
    获取当前项目的配置信息,并对内容进行缓存，避免重复读取
    """
    settings = Settings()
    return settings
