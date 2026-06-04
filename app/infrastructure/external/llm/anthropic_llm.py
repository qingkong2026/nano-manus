import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from anthropic import AsyncAnthropic
from anthropic.types.beta.beta_tool_bash_20250124_param import Dict

from app.application.errors.exceptions import ServerRequestError
from app.domain.external.llm import LLM
from app.domain.models import LLMConfig

logger = logging.getLogger(__name__)


class AnthropicLLM(LLM):
    def __init__(self, llm_config: LLMConfig) -> None:
        self._client = AsyncAnthropic(
            base_url=str(llm_config.base_url), api_key=llm_config.api_key
        )
        self._model_name = llm_config.model_name
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens
        self._timeout = 3600

    async def invoke(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        使用异步Anthropic LLM 接口发起块响应
        """
        try:
            # 1.检测是否传递了工具列表
            if tools:
                logger.info(
                    f"调用 Anthropic客户端向 LLM 发起请求，携带工具信息：{tools}"
                )
                response = await self._client.messages.create(
                    model=self._model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    output_config=response_format,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    timeout=self._timeout,
                )

            else:
                logger.info("调用 Anthropic客户端向 LLM 发起请求，未携带工具信息")
                response = await self._client.messages.create(
                    model=self._model_name,
                    messages=messages,
                    output_config=response_format,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    timeout=self._timeout,
                )
            logger.info(f"Anthropic 客户端响应：{response.model_dump()}")
            return {
                block.type: block.text
                for block in response.content
                if block.type == "text"
            }
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
