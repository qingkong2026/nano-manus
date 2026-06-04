from typing import Any, Protocol, List, Dict, Optional, Union

class LLM(Protocol):
    """用于agent应用与LLM进行交互的接口协议"""

    async def invoke(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """传递消息列表、工具列表、响应格式、工具选择策略，调用 LLM 接口"""
        ...

    @property
    def model_name(self) -> str:
        """read-only,返回模型名称"""
        ...

    @property
    def temperature(self) -> float:
        """read-only,返回温度"""
        ...

    @property
    def max_tokens(self) -> int:
        """read-only,返回最大token数"""
        ...



