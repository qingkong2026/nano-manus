from typing import List

from pydantic import BaseModel, Field

from app.domain.models.app_config import  MCPTransport

class ListMCPServerItem(BaseModel):
    """MCP服务列表条目选项"""

    server_name: str = ""   # 服务名字
    enabled: bool = True    # 启用状态
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP   # 传输协议
    tools: List[str] = Field(default_factory=list)   # 工具名字协议

class ListMCPServerResponse(BaseModel):
    """获取MCP服务列表响应结构"""

    mcp_servers: List[ListMCPServerItem] = Field(default_factory=list)