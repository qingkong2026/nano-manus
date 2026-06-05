import json
import logging
from pathlib import Path
from typing import Optional

from filelock import FileLock, Timeout

from app.application.errors.exceptions import ServerRequestError
from app.domain.models import AgentConfig, AppConfig, LLMConfig
from app.domain.repository import AppConfigRepository

logger = logging.getLogger(__name__)


class FileAppConfigRepository(AppConfigRepository):
    """基于本地文件的App配置数据仓储层实现"""

    def __init__(self, config_path: str) -> None:
        # 1.获取当前项目的根目录
        root_dir = Path.cwd()

        # 2.拼接配置文件路径并校验基础信息
        self._config_path = root_dir.joinpath(config_path)
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock_file = self._config_path.with_suffix(".lock")
        self._lock = FileLock(self._lock_file, timeout=5)

    def _create_default_app_config_if_not_exists(self) -> None:
        """如果配置文件不存在，则创建默认配置"""
        if not self._config_path.exists():
            default_app_config = AppConfig(
                llm_config=LLMConfig(), agent_config=AgentConfig()
            )
            self.save(default_app_config)

    def load(self) -> Optional[AppConfig]:
        """从本地JSON文件中加载应用配置"""
        # 1.创建默认配置确保文件存在
        self._create_default_app_config_if_not_exists()

        try:
            # 2.读取配置文件
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data is not None:
                    return AppConfig.model_validate(data)
                else:
                    return None
        except Exception as e:
            logger.error(f"读取应用配置失败：str{e}")
            raise ServerRequestError("读取应用配置失败，请稍后重试")

    def save(self, app_config: AppConfig) -> None:
        """将应用配置保存到本地JSON文件"""

        try:
            with self._lock:
                # 1.将 app_config 转换成 json
                data_to_dump = app_config.model_dump(mode="json")
                # 2.打开 json 文件并写入数据
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(
                        data_to_dump, f, indent=2, ensure_ascii=False, sort_keys=False
                    )
        except Timeout:
            logger.error("获取锁超时，写入配置文件失败")
            raise ServerRequestError("获取锁超时，写入配置文件失败，请稍后重试")
        except Exception as e:
            logger.error(f"写入配置文件失败：str{e}")
            raise ServerRequestError("写入配置文件失败，请稍后重试")
