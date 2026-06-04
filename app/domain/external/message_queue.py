from typing import Protocol, Tuple

from typing_extensions import Any

class MessageQueue(Protocol):
    """消息队列协议"""
    
    async def put(self, message: Any) -> str:
        """往消息队列中添加一条消息"""
        ...

    async def get(self, start_id: str = None, block_ms: int = None) -> Tuple[str, Any]:
        """根据传递的开始id+阻塞时间，获取一条消息"""
        ...

    async def pop(self) -> Tuple[str, Any]:
        """获取并移除消息队列中的第一条消息"""
        ...

    async def clear(self) -> None:
        """清空消息队列"""
        ...

    async def is_empty(self) -> bool:
        """判断消息队列是否为空"""
        ...

    async def size(self) -> int:
        """获取消息队列中消息的数量"""
        ...

    async def delete_message(self, message_id: str) -> bool:
        """删除指定id的消息"""
        ...

    
