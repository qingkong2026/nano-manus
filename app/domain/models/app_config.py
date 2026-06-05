from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LLMConfig(BaseModel):
    """大语言模型配置"""

    base_url: HttpUrl = HttpUrl(url="https://api.minimaxi.com/anthropic")
    api_key: str = ""
    model_name: str = "MiniMax-M3"
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=8192, ge=0)


class AgentConfig(BaseModel):
    """Agent通用配置"""

    max_iterations: int = Field(default=100, gt=0, lt=1000)  # 最大迭代次数
    max_retries: int = Field(default=3, gt=1, lt=10)  # LLM/工具最大重试次数
    max_search_results: int = Field(default=10, gt=1, lt=30)  # 最大搜索结果数


class AppConfig(BaseModel):
    """App配置信息，包含Agent配置、LLM配置、A2A配置、MCP服务配置"""

    llm_config: LLMConfig
    agent_config: AgentConfig

    # pydantic 配置，允许传递额外的字段初始化
    model_config = ConfigDict(extra="allow")
