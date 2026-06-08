import logging
import os
import httpx
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any

from mcp import ClientSession, StdioServerParameters, Tool, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from app.application.errors.exceptions import NotFoundError
from app.domain.models import MCPConfig, MCPServerConfig, MCPTransport
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseToolSet

logger = logging.getLogger(__name__)


class MCPClientManage:
    """MCP客户端管理器"""

    def __init__(self, mcp_config: Optional[MCPConfig] = None) -> None:
        """构造函数，完成 MCP 客户端管理器的初步初始化"""

        self._mcp_config: MCPConfig = mcp_config  # mcp 配置信息
        self._exit_stack: AsyncExitStack = AsyncExitStack()  # 异步上下文管理器
        self._clients: Dict[str, ClientSession] = {}  # 缓存的客户端会话
        self._tools: Dict[str, List[Tool]] = {}  # 缓存的 MCP 工具参数声明
        self._initialized: bool = False  # 是否初始化标识

    @property
    def tools(self) -> Dict[str, List[Tool]]:
        """read-only, 返回缓存的 MCP 工具参数声明，键就是服务名字，值就是服务对应的工具声明"""
        return self._tools

    async def initialize(self) -> None:
        """初始化函数，用于连接所有配置的 MCP 服务器"""

        # 1.检查下是否已经初始化成功
        if self._initialized:
            return

        try:
            # 2.记录日志并连接 MCP 服务器
            logger.info(
                f"从 config.json 中加载了 {len(self._mcp_config.mcpServers)} 个 MCP 服务器"
            )
            await self._connect_mcp_servers()
            self._initialized = True
            logger.info("MCP 客户端管理器初始化成功")
        except Exception as e:
            logger.error(f"MCP客户端管理器加载失败：{str(e)}")
            raise

    async def _connect_mcp_servers(self) -> None:
        """连接所有配置的 MCP 服务器"""

        # 1.循环遍历所有 MCP 服务器。不用管 enabled 的状态，会在外部执行时进行筛选
        for server_name, server_config in self._mcp_config.mcpServers.items():
            try:
                # 2.根据 server_name + mcp_config 连接到 MCP 服务器
                await self._connect_mcp_server(server_name, server_config)
            except Exception as e:
                logger.error(f"连接 MCP 服务器[{server_name}]失败：{str(e)}")
                continue

    async def _connect_mcp_server(
        self, server_name: str, server_config: MCPServerConfig
    ) -> None:
        """根据 server_name 和 server_config 连接到 MCP 服务器"""
        try:
            # 1.获取 mcp 服务器的传输协议
            transport = server_config.type

            # 2.根据传输协议调用不同的方法创建 MCP 客户端
            if transport == MCPTransport.STDIO:
                await self._connect_stdio_server(server_name, server_config)
            elif transport == MCPTransport.SSE:
                await self._connect_sse_server(server_name, server_config)
            elif transport == MCPTransport.STREAMABLE_HTTP:
                await self._connect_streamable_http_server(server_name, server_config)
            else:
                raise ValueError(
                    f"{server_name}使用了不支持的 MCP 传输协议：{transport}"
                )
        except Exception as e:
            logger.error(f"连接 MCP 服务器[{server_name}]失败：{str(e)}")
            raise

    async def _connect_stdio_server(
        self, server_name: str, server_config: MCPServerConfig
    ) -> None:
        """根据 server_name 和 server_config 连接到 STDIO MCP 服务器"""

        # 1.从配置中提取相关的命令信息
        command = server_config.command
        args = server_config.args
        env = server_config.env

        # 2.检查 command 是否存在
        if not command:
            raise ValueError("连接 stdio-mcp服务器需要配置 command")

        # 3.构建 stdio 连接参数
        server_parameters = StdioServerParameters(
            command=command,
            args=args,
            env={**os.environ, **(env or {})},
        )

        # 4.连接 stdio 服务器
        try:
            # 使用异步上下文管理器创建传输协议
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_parameters)
            )
            read_stream, write_stream = stdio_transport

            # 根据读取与写入流构建会话
            session: ClientSession = await self._exit_stack.enter_async_context(
                ClientSession(read_stream=read_stream, write_stream=write_stream)
            )

            # 初始化 MCP 服务会话
            await session.initialize()

            # 缓存对应的 mcp 连接客户端
            self._clients[server_name] = session

            # 缓存对应 mcp 服务的工具列表
            await self._cache_mcp_server_tools(server_name, session)
            logger.info(f"连接 stdio-mcp服务器成功: {server_name}")
        except Exception as e:
            logger.error(f"连接 stdio-mcp 服务器失败: {e}")
            raise

    async def _connect_sse_server(
        self, server_name: str, server_config: MCPServerConfig
    ) -> None:
        """根据 server_name 和 server_config 连接到 SSE MCP 服务器"""
        # 1.判断 url 是否存在
        url = server_config.url
        if not url:
            raise ValueError("连接sse-mcp服务器需要配置 url")

        try:
            # 2.建立 sse 连接
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(url=url, headers=server_config.headers)
            )

            read_stream , write_stream = sse_transport

            # 创建客户端会话
            session: ClientSession = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await session.initialize()

            # 缓存 sse 客户端会话
            self._clients[server_name] = session

            # 缓存对应 mcp 服务的工具列表
            await self._cache_mcp_server_tools(server_name, session)
            logger.info(f"连接 sse-mcp服务器成功: {server_name}")
            
        except Exception as e:
            logger.error(f"连接 sse-mcp 服务器失败: {e}")
            raise

    async def _connect_streamable_http_server(
        self, server_name: str, server_config: MCPServerConfig
    ) -> None:
        """根据 server_name 和 server_config 连接到 Streamable HTTP MCP 服务器"""
        
        # 1.判断 url 是否存在
        url = server_config.url
        if not url:
            raise ValueError("连接 streamable-http-mcp 服务器需要配置 url")

        try:

            # 创建 httpx.AsyncClient
            custom_http_client = httpx.AsyncClient(
                headers=server_config.headers,
                # 如需 basic auth 也在这里配置
                # auth=httpx.BasicAuth("user", "pass")
            )
            # 2.连接 streamable-http 服务
            streamable_http_transport = await self._exit_stack.enter_async_context(
                streamable_http_client(url=url, http_client=custom_http_client)
            )

            # 获取输入与输出流
            if len(streamable_http_transport) == 3:
                read_stream , write_stream, _ = streamable_http_transport
            else:
                read_stream , write_stream = streamable_http_transport

            # 创建 streamable-http 客户端
            session: ClientSession = await self._exit_stack.enter_async_context(
                ClientSession(read_stream=read_stream, write_stream=write_stream)
            )

            await session.initialize()

            # 缓存对应的 mcp 连接客户端
            self._clients[server_name] = session

            # 缓存对应的工具列表
            await self._cache_mcp_server_tools(server_name, session)
            logger.info(f"成功连接 streamable-http-mcp 服务器: {server_name}")
        except Exception as e:
            logger.error(f"连接 streamable-http-mcp 服务器失败: {e}")
            raise

    async def _cache_mcp_server_tools(
        self, server_name: str, session: ClientSession
    ) -> None:
        """缓存对应 mcp 服务的工具列表"""
        
        try:
            tools_response = await session.list_tools()
            tools = tools_response.tools if tools_response else []
            self._tools[server_name] = tools
            logging.info(f"MCP 服务器[{server_name}] 提供了{len(tools)}个工具")
        except Exception as e:
            logger.error(f"获取 MCP 服务器[{server_name}] 工具列表失败: {str(e)}")
            raise


    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有 MCP 工具列表，返回 LLM 可以使用的工具参数声明列表并处理 MCP 的名字"""
        all_tools = []

        for server_name, tools in self._tools.items():
            for tool in tools:
                # 修改工具名字加上 mcp_ 前缀 + 服务名字
                if server_name.startswith("mcp_"):
                    tool_name = f"{server_name}_{tool.name}"
                else:
                    tool_name = f"mcp_{server_name}_{tool.name}"

                description = f"[{server_name}] {tool.description or tool.name} "
                # 生成 Anthropic 工具描述
                tool_schema = {
                    "name": tool_name,
                    "description": description,
                    "input_schema": tool.inputSchema,
                }
                all_tools.append(tool_schema)

        return all_tools


    async def invoke(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """根据传递的 tool_name 和 arguments 调用对应的 MCP 工具"""
        try:
            # 1.定义变量存储原始的服务名字和工具名字
            original_server_name = None
            original_tool_name = None

            for server_name in self._mcp_config.mcpServers.keys():
                # 为 server_name 组装前缀
                expected_prefix = server_name if server_name.startswith("mcp_") else f"mcp_{server_name}"
                
                if tool_name.startswith(f"{expected_prefix}_"):
                    original_server_name = server_name
                    original_tool_name = tool_name[len(expected_prefix) + 1:]
                    break

            # 判断服务名字 + 工具是否都存在
            if not original_server_name or not original_tool_name:
                raise NotFoundError(f"未找到对应的 MCP 工具[{tool_name}]")

            # 获取该工具所属的会话
            session = self._clients.get(original_server_name)
            if not session:
                return ToolResult(
                    success=False,
                    message=f"未找到对应的 MCP 服务[{original_server_name}]"
                )

            # 调用工具
            result = await session.call_tool(original_tool_name, arguments)

            if result:
                # 处理 MCP 工具生成的 content
                content = []
                if hasattr(result, "content") and result.content:
                    for block in result.content:
                        if hasattr(block, "text"):
                            content.append(block.text)
                        else:
                            content.append(str(block))
                            
                return ToolResult(
                    success=True,
                    data="\n".join(content) if content else "工具执行成功",
                )
            else:
                return ToolResult(
                    success=True,
                    data="工具执行成功",
                )
            
        except Exception as e:
            logger.error(f"调用 MCP 工具[{tool_name}] 失败: {str(e)}")
            return ToolResult(
                success=False,
                message=f"调用 MCP 工具[{tool_name}] 失败: {str(e)}"
            )


    async def cleanup(self) -> None:
        """清理函数，用于关闭所有 MCP 客户端连接"""
        try:
            await self._exit_stack.aclose()
            self._clients.clear()
            self._tools.clear()
            self._initialized = False
            logger.info("清理 MCP 客户端管理器成功")
        except Exception as e:
            logger.error(f"清理 MCP 客户端管理器失败: {str(e)}")


class MCPToolSet(BaseToolSet):
    """MCP工具包,包含所有已配置+亦启动的 MCP 工具"""
    name: str = "mcp"

    def __init__(self) -> None:
        super().__init__()
        self._initialized: bool = False
        self._tools = []
        self._manager: MCPClientManage = None

    async def initialize(self, mcp_config: Optional[MCPConfig]) -> None:
        """初始化 MCP 工具"""
        if not self._initialized:
            self._manager = MCPClientManage(mcp_config=mcp_config)
            await self._manager.initialize()

            self._tools = await self._manager.get_all_tools()
            self._initialized = True

    def get_tools(self) -> List[Dict[str, Any]]:
        """同步获取工具包下的所有工具列表"""
        return self._tools

    def has_tool(self, tool_name: str) -> bool:
        """传递工具名字判断工具是否存在"""
        for tool in self._tools:
            if tool["name"] == tool_name:
                return True

        return False

    async def invoke(self, tool_name: str, **kwargs) -> ToolResult:
        """传递工具名字 + 参数调用 MCP 工具并获取结果"""
        return await self._manager.invoke(tool_name, **kwargs)

    async def cleanup(self) -> None:
        """清除 MCP 工具资源"""
        if self._manager:
            await self._manager.cleanup()