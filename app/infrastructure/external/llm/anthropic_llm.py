import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from anthropic import AsyncAnthropic

from app.application.errors.exceptions import ServerRequestError
from app.domain.external.llm import LLM
from app.domain.models import LLMConfig
from app.domain.models.memory import (
    BlockType,
    MessageRole,
    UniformMessage,
    UniformTextBlock,
    UniformToolUseBlock,
)

logger = logging.getLogger(__name__)


class AnthropicLLM(LLM):
    def __init__(self, llm_config: LLMConfig, **kwargs) -> None:
        self._client = AsyncAnthropic(
            base_url=str(llm_config.base_url),
            api_key=llm_config.api_key,
            **kwargs,
        )
        self._model_name = llm_config.model_name
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens
        self._timeout = 3600

        self._total_input_tokens = 0
        self._total_input_tokens = 0

    def _to_native_messages(self, uniform_messages: List[UniformMessage]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """将 UniformMessage 转换成 厂商的规范"""

        system_prompt_pieces = []
        native_messages = []

        for msg in uniform_messages:
            # 转换1: 抓取系统全局预设，拼成一个大文本
            if msg.role == MessageRole.SYSTEM:
                for block in msg.content:
                    if block in msg.content:
                        system_prompt_pieces.append(block.text)
                continue

            # 转换2：按 block 逐个映射到物理字段上
            api_blocks = []
            for block in msg.content:
                if block.type == BlockType.TEXT:
                    api_blocks.append({"type": "text", "text": block.text})

                elif block.type == BlockType.TOOL_USE:
                    api_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.arguments,
                    })

                elif block.type == BlockType.TOOL_RESULT:
                    api_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": block.content,
                        "is_error": block.is_error
                    })

            role_str = msg.role.value
            if any(block.type == BlockType.TOOL_RESULT for block in msg.content):
                role_str = "user"

            native_messages.append({
                "role": role_str,
                "content": api_blocks
            })

        system_prompt = "\n".join(system_prompt_pieces) if system_prompt_pieces else None

        return system_prompt, native_messages

    def _convert_tool_choice(self, tool_choice: Optional[Union[str, Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """将外界通用的 tool_choice 策略平滑翻译为 Anthropic 的独家字段"""
        if not tool_choice:
            return None

        # 如果传递的是简单字段，比如 auto 或 any
        if isinstance(tool_choice, str):
            if tool_choice in ["auto", "any"]:
                return {"type": tool_choice}
            # 如果传递的是特定的工具名
            return {"type": "tool", "name": tool_choice}

        return tool_choice

    def _uniform_response(self, response) -> UniformMessage:
        """将 Anthropic 客户端的响应转换为统一的消息格式"""
        uniform_blocks = []

        for block in response.content:
            if block.type == "text":
                uniform_blocks.append(UniformTextBlock(text=block.text))
            elif block.type == "tool_use":
                uniform_blocks.append(
                    UniformToolUseBlock(
                        id=block.id,
                        name=block.name,
                        arguments=block.arguments,
                    )
                )

        return UniformMessage(
            role=MessageRole.ASSISTANT,
            content=uniform_blocks,
        )

    async def invoke(
        self,
        messages: List[UniformMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> UniformMessage:
        """
        使用异步Anthropic LLM 接口发起块响应
        """
        try:

            system_prompt, native_messages = self._to_native_messages(messages)
            
            kwargs = {
                "model": self._model_name,
                "messages": native_messages,
                "temperature": self._temperature,
                "max_tokens": self._max_tokens,
                "timeout": self._timeout,
            }

            # 1.检测是否传递了工具列表
            if system_prompt:
                kwargs["system"] = system_prompt
            if response_format:
                kwargs["output_config"] = response_format
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            logger.debug(f"调用 Anthropic客户端向 LLM 发起请求，携带工具信息：{tools if tools else '无'}")
            response = await self._client.messages.create(**kwargs)

            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            logger.debug(f"Token 统计 - 本次 Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")

            uniform_response = self._uniform_response(response)

            return uniform_response
        except Exception as e:
            logger.error(f"Anthropic 客户端调用失败：{e}")
            raise ServerRequestError("调用 Anthropic 客户端失败")

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def temperature(self) -> float:
        return self._temperature
