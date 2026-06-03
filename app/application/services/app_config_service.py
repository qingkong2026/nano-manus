from app.domain.models import AppConfig, LLMConfig
from app.domain.repository import AppConfigRepository

class AppConfigService:
    """应用配置服务"""

    def __init__(self, app_config_repo: AppConfigRepository) -> None:
        """构造函数，完成应用配置服务的初始化"""
        self.app_config_repo = app_config_repo

    def _load_app_config(self) -> AppConfig:
        """加载并获取所有的应用配置"""
        return self.app_config_repo.load()

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        return self._load_app_config().llm_config

    def update_llm_config(self, llm_config: LLMConfig) -> LLMConfig:
        """根据传递的llm_config更新语言模型供应商配置"""
        # 1.加载应用配置
        app_config = self._load_app_config()
        if llm_config.api_key is None:
            llm_config.api_key = app_config.llm_config.api_key
        app_config.llm_config = llm_config
        # 2.保存应用配置
        self.app_config_repo.save(app_config)
        # 3.返回更新后的LLM配置
        return app_config.llm_config