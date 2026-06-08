from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, HttpUrl , model_validator
from typing import Dict ,Any

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

class MCPTransport(str, Enum):
    """MCP传输类型枚举"""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"

class MCPServerConfig(BaseModel):
    """MCP单条服务配置"""
    # 通用字段配置
    type: MCPTransport = MCPTransport.STREAMABLE_HTTP
    enabled: bool = True
    description: Optional[str] = None
    env: Optional[Dict[str, Any]] = None

    # stdio 配置
    command: Optional[str] = None
    args: Optional[List[str]] = None

    # streamable_http 与 sse 配置
    url: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_mcp_server_config(self):
        """校验 mcp_server_config 的相关信息"""
        if self.type in [MCPTransport.SSE, MCPTransport.STREAMABLE_HTTP]:
            if not self.url:
                raise ValueError("在 sse 或 streamable_http 传输协议中必须传递 url")
        if self.type == MCPTransport.STDIO:
            if not self.command:
                raise ValueError("在 stdio 中必须传递 command")
        return self


class MCPConfig(BaseModel):
    """应用MCP配置"""
    mcpServers: Dict[str, MCPServerConfig] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class AppConfig(BaseModel):
    """App配置信息，包含Agent配置、LLM配置、A2A配置、MCP服务配置"""

    llm_config: LLMConfig
    agent_config: AgentConfig
    mcp_config: MCPConfig

    # pydantic 配置，允许传递额外的字段初始化
    model_config = ConfigDict(extra="allow")
