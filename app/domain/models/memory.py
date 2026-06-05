import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# todo: 这里要考虑 Anthropic 格式和 OpenAI 格式的兼容问题，
class Memory(BaseModel):
    """记忆类，定义Agent的记忆基础信息"""

    messages: List[Dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def get_messages_role(cls, message: Dict[str, Any]) -> str:
        """根据传递的消息来获取消息的角色信息"""
        return message.get("role")

    def add_message(self, message: Dict[str, Any]) -> None:
        """往记忆中添加一条消息"""
        self.messages.append(message)

    def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        """往记忆中添加多条消息"""
        self.messages.extend(messages)

    def get_messages(self) -> List[Dict[str, Any]]:
        """获取记忆中的所有消息列表"""
        return self.messages

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """获取记忆中的最后一条消息，如果不存在则返回 None"""
        return self.messages[-1] if len(self.messages) > 0 else None

    def roll_back(self) -> None:
        """回滚记忆，删除最后一条消息"""
        self.messages = self.messages[:-1]

    def compact(self) -> None:
        """记忆压缩，将记忆中执行的工具(eg:搜索/网页源码获取/浏览器访问结果等)的结果压缩，持久化"""
        # 1.循环遍历所有的消息列表
        for message in self.messages:
            # 2.判断角色的消息是否为 tool
            if self.get_messages_role(message) == "tool":
                # todo: 工具名字列表待定
                if message.get("name") in []:
                    # todo: 工具调用结果待定
                    message["content"] = "(remove)"
                    logger.info(f"从记忆中移除对应的工具的结果：{message['name']}")

    def empty(self) -> bool:
        """read-only, 检查记忆是否为空"""
        return len(self.messages) == 0
