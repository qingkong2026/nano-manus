import logging
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BlockType(str, Enum):
    """块类型枚举"""

    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class MessageRole(str, Enum):
    """消息角色枚举"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UniformTextBlock(BaseModel):
    """纯文本内容块：存放 LLM 思考、文本回复、用户原始 prompt"""

    type: Literal[BlockType.TEXT] = BlockType.TEXT
    text: str = ""


class UniformToolUseBlock(BaseModel):
    """工具调用内容块：存放 LLM 调用工具的请求"""

    type: Literal[BlockType.TOOL_USE] = BlockType.TOOL_USE
    tool_use_id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = Field(default_factory=dict)


class UniformToolResultBlock(BaseModel):
    """工具执行结果内容块：存放工具执行的结果"""

    type: Literal[BlockType.TOOL_RESULT] = BlockType.TOOL_RESULT
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False


UniformContentBlock = Union[
    UniformTextBlock, UniformToolUseBlock, UniformToolResultBlock
]


# 统一消息定义
class UniformMessage(BaseModel):
    """统一消息模型：封装了消息的角色、内容和类型"""

    role: MessageRole
    content: List[UniformContentBlock] = Field(default_factory=list)

    @classmethod
    def create_text(cls, role: MessageRole, text: str) -> "UniformMessage":
        """快捷工厂方法：快速创建一条单文本块的消息"""
        return cls(role=role, content=[UniformTextBlock(text=text)])

    @classmethod
    def create_tool_result(cls, results: List[UniformToolResultBlock]) -> "UniformMessage":
        """快速创建 Anthropic 协议的工具执行结果块"""
        return cls(role=MessageRole.USER, content=list(results))

# todo: 这里要考虑 Anthropic 格式和 OpenAI 格式的兼容问题，
class Memory(BaseModel):
    """记忆类，定义Agent的记忆基础信息"""

    messages: List[UniformMessage] = Field(default_factory=list)

    @classmethod
    def get_messages_role(cls, message: UniformMessage) -> str:
        """根据传递的消息来获取消息的角色信息"""
        return message.role.value

    def add_message(self, message: Union[UniformMessage, Dict[str, Any]]) -> None:
        """往记忆中添加一条消息"""
        if isinstance(message, dict):
            message = UniformMessage.model_validate(message)
        self.messages.append(message)

    def add_messages(
        self, messages: Sequence[Union[UniformMessage, Dict[str, Any]]]
    ) -> None:
        """往记忆中添加多条消息"""
        for msg in messages:
            self.add_message(msg)

    def get_messages(self) -> List[UniformMessage]:
        """获取记忆中的所有消息列表"""
        return self.messages

    def get_last_message(self) -> Optional[UniformMessage]:
        """获取记忆中的最后一条消息，如果不存在则返回 None"""
        return self.messages[-1] if len(self.messages) > 0 else None

    def roll_back(self) -> None:
        """回滚记忆，删除最后一条消息"""
        if self.messages:
            self.messages.pop()

    def empty(self) -> bool:
        """read-only, 检查记忆是否为空"""
        return len(self.messages) == 0

    def clear(self) -> None:
        """清空记忆"""
        self.messages.clear()

    def compact(self, target_tools: List[str]) -> None:
        """记忆压缩，将记忆中执行的工具(eg:搜索/网页源码获取/浏览器访问结果等)的结果压缩，持久化"""
        # 1.循环遍历所有的消息列表
        tool_map = {}

        compact_count = 0
        for message in self.messages:
            for block in message.content:
                if isinstance(block, UniformToolResultBlock):
                    tool_name = tool_map[block.id]
                    if tool_name in [] and not block.content.startswith(
                        "[Content omitted]"
                    ):
                        old_len = len(block.content)
                        block.content = (
                            f"[Content omitted by Manus Memory Compactor. "
                            f"Tool '{tool_name}' (ID: {block.id}) executed successfully. "
                            f"Original raw output size was {old_len} chars.]"
                        )
                        compact_count += 1
        if compact_count > 0:
            logger.info(f"Memory: 成功压缩了 {compact_count} 个冗长的工具返回块！")
