import asyncio
import logging
import uuid
from abc import ABC
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.domain.external.json_parser import JSONParser
from app.domain.external.llm import LLM
from app.domain.models import AgentConfig
from app.domain.models.event import (
    ErrorEvent,
    Event,
    MessageEvent,
    ToolEvent,
    ToolEventStatus,
)
from app.domain.models.memory import (
    BlockType,
    Memory,
    MessageRole,
    UniformMessage,
    UniformTextBlock,
    UniformToolResultBlock,
    UniformToolUseBlock,
)
from app.domain.models.message import Message
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseToolSet

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent智能体基类"""

    name: str = ""  # 智能体名字
    _system_prompt: str = ""  # 系统预设 prompt
    _format: Optional[str] = None  # Agent 响应格式
    _retry_interval: float = 1.0  # 重试间隔
    _tool_choice: Optional[str] = None  # 强制使用工具

    def __init__(
        self,
        agent_config: AgentConfig,  # Agent 通用配置
        llm: LLM,  # 大语言模型协议
        memory: Memory,  # 记忆
        json_parser: JSONParser,  # JSON输出解析器
        tool_sets: List[BaseToolSet],  # 工具列表
    ) -> None:
        """构造函数，完成 Agent 的初始化"""
        self._agent_config = agent_config
        self._llm = llm
        self._memory = memory
        self._json_parser = json_parser
        self._tool_sets = tool_sets

    @property
    def memory(self) -> Memory:
        """read-only, 返回记忆"""
        return self._memory

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """获取Agent所有可用的工具列表声明/Schema"""
        available_tools = []
        for tool_set in self._tool_sets:
            available_tools.extend(tool_set.get_tools_schema())
        return available_tools

    def _get_tool_set(self, tool_name: str) -> BaseToolSet:
        """获取对应工具所在的工具包"""
        for tool_set in self._tool_sets:
            if tool_set.has_tool(tool_name):
                return tool_set

        raise ValueError(f"未知工具：{str(tool_name)}")

    async def _invoke_tool(
        self, tool_set: BaseToolSet, tool_name: str, tool_input: Dict[str, Any]
    ) -> ToolResult:
        """传递工具集合 + 工具名字,调用指定工具"""
        # 1.执行循环调用工具获取结果
        err = ""
        for _ in range(self._agent_config.max_retries):
            try:
                return await tool_set.invoke(tool_name=tool_name, **tool_input)
            except Exception as e:
                err = str(e)
                logger.exception(f"调用工具[{tool_name}]出错，错误：{str(e)}")
                await asyncio.sleep(self._retry_interval)
                continue

        # 2.循环最大重试次数后，没有结果则将错误作为工具执行结果
        return ToolResult(success=False, message=err)

    async def _invoke_llm(
        self, next_message: UniformMessage, format: Optional[str] = None
    ) -> UniformMessage:
        """调用大语言模型并处理记忆内容"""
        # 1.将消息添加到记忆中
        if next_message:
            await self._add_to_memory([next_message])

        # 2.组装大语言模型的响应格式
        response_format = {"type": format} if format else None

        # 3.循环向 LLM 发起提问直到最大重试次数
        for attempt in range(self._agent_config.max_retries):
            try:
                # 4.调用大语言模型，将强类型记忆直接灌入（LLM 模块内部做非对称翻译）
                messages = self.memory.get_messages()
                response_message = await self._llm.invoke(
                    messages=messages,
                    tools=self._get_available_tools(),
                    response_format=response_format,
                    tool_choice=self._tool_choice,
                )

                # 防御机制：处理 LLM 吐出完全空内容的情况
                if not response_message.content:
                    logger.warning("LLM 回复了完全空的内容，执行自动重试")
                    await asyncio.sleep(self._retry_interval)
                    continue

                # 生成成功
                await self._add_to_memory(messages=[response_message])
                return response_message

            except Exception as e:
                logger.error(f"调用 LLM 发生错误：{str(e)}")
                await asyncio.sleep(self._retry_interval)
                continue

        # 4.所有重试都失败了，返回一个错误信息
        error_message = UniformMessage(
            role=MessageRole.ASSISTANT,
            content=[UniformTextBlock(text="调用模型失败，请稍后重试")],
        )
        logger.critical(
            f"LLM 调用已达到最大重试次数 {self._agent_config.max_retries}，无法获取有效响应"
        )
        return error_message

    async def _add_to_memory(self, messages: List[UniformMessage]) -> None:
        """将对应的信息添加到记忆中"""
        # 1.检查记忆的消息列表是否为空，如果为空则需要添加预设系统 prompt 作为初始记忆
        if self._memory.empty:
            self._memory.add_message(
                UniformMessage.create_text(MessageRole.SYSTEM, self._system_prompt)
            )
        # 2.将正常消息添加到记忆中
        self._memory.add_messages(messages)

    async def compact_memory(self) -> None:
        """压缩 Agent 的记忆"""
        self._memory.compact(target_tools=[])

    async def roll_back(self, message: Message) -> None:
        """Agent的状态回滚，该函数用于确保Agent的消息列表是正确，用于发送新消息、暂停/停止任务"""
        # 1.取出记忆中最后一条消息，检查是否是有工具调用
        last_message = self._memory.get_last_message()
        if not last_message:
            return

        if last_message.role != MessageRole.ASSISTANT:
            return

        tool_use_blocks = [
            block
            for block in last_message.content
            if block.type == BlockType.TOOL_USE or block.type == "tool_use"
        ]

        if not tool_use_blocks:
            return

        has_normal_tool = any(
            block.name != "message_ask_user" for block in tool_use_blocks
        )

        if has_normal_tool:
            self._memory.roll_back()
            return

        tool_result_blocks = [
            UniformToolResultBlock(
                tool_use_id=block.tool_use_id,
                content=message.model_dump_json(),
                is_error=False,
            )
            for block in tool_use_blocks
        ]

        self._memory.add_message(UniformMessage.create_tool_result(tool_result_blocks))

    async def invoke(
        self, query: str, format: Optional[str] = None
    ) -> AsyncGenerator[Event]:
        """传递消息+响应格式，调用程序生成异步迭代内容"""

        # 1.需要判断下是否传递了 format
        format = format if format else self._format

        user_start_message = UniformMessage.create_text(
            role=MessageRole.USER, text=query
        )

        # 2.调用大语言模型并获取响应内容
        message = await self._invoke_llm(next_message=user_start_message, format=format)

        # 3.循环遍历直到最大迭代次数
        for current_iter in range(self._agent_config.max_iterations):
            # 4.如果响应内容无工具调用则表示 LLM 生成了文本回答，这时候就是最终答案
            tool_calls = [
                block
                for block in message.content
                if isinstance(block, UniformToolUseBlock)
            ]

            if not tool_calls:
                logger.debug("无工具调用，正常结束")
                break

            # 5.循环遍历工具参数并执行
            tool_messages: List[UniformToolResultBlock] = []
            for tool_call in tool_calls:
                # 6.获取工具 id , 名字，参数信息
                tool_use_id = tool_call.tool_use_id if tool_call else str(uuid.uuid4())
                tool_name = tool_call.name
                tool_input = tool_call.arguments

                # 7.获取 Agent 中对应的工具集合
                tool_set = self._get_tool_set(tool_name)

                # 8.返回工具即将调用事件
                yield ToolEvent(
                    tool_use_id=tool_use_id,
                    tool_set_name=tool_set.name,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    status=ToolEventStatus.CALLING,
                )

                # 9.调用工具并获取结果
                result = await self._invoke_tool(
                    tool_set=tool_set, tool_name=tool_name, tool_input=tool_input
                )

                # 10.返回工具调用完成事件
                yield ToolEvent(
                    tool_use_id=tool_use_id,
                    tool_set_name=tool_set.name,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_result=result,
                    status=ToolEventStatus.CALLED,
                )

                # 11.组装工具响应
                tool_messages.append(
                    UniformToolResultBlock(
                        tool_use_id=tool_use_id, content=result.model_dump_json()
                    )
                )

            tool_results_message = UniformMessage.create_tool_result(tool_messages)

            # 12.进入下一轮迭代，把打包好的工具消息直接灌回给大模型进行收口/进一步思考
            message = await self._invoke_llm(next_message=tool_results_message)

            # 12. 可选：在此处执行自动记忆压缩（防爆 Token）
            # await self.compact_memory()
        else:
            # 13.超过最大迭代次数后，抛出异常
            yield ErrorEvent(
                error=f"Agent迭代次数超过最大迭代次数：{self._agent_config.max_iterations}，任务处理失败"
            )

        text_content = "".join(
            block.text
            for block in message.content
            if isinstance(block, UniformTextBlock)
        )

        yield MessageEvent(
            role="assistant",
            message=text_content,
        )
