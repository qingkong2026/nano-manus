from typing import Optional, Protocol

from abs import ABC, abstractmethod

from .message_queue import MessageQueue


class TaskRunner(ABC):
    """任务运行器，负责任务的执行、关心的是如何执行任务、销毁任务释放资源"""

    @abstractmethod
    async def execute(self, task: "Task") -> None:
        """调用任务并执行"""
        raise NotImplementedError

    @abstractmethod
    async def destroy(self) -> None:
        """销毁任务并释放资源，包括：关闭网络连接、释放内存、清理临时内存、清理后台进程等"""
        raise NotImplementedError

    @abstractmethod
    async def on_done(self, task: "Task") -> None:
        """任务执行完成后的回调函数"""
        raise NotImplementedError


class Task(Protocol):
    """任务协议，定义任务的执行接口"""

    async def run(self) -> None:
        """执行任务"""
        ...

    async def cancel(self) -> None:
        """取消当前任务"""
        ...

    @property
    def input_stream(self) -> MessageQueue:
        """read-only, 返回任务的输入流"""
        ...

    @property
    def output_stream(self) -> MessageQueue:
        """read-only, 返回任务的输出流"""
        ...

    @property
    def id(self) -> str:
        """read-only, 返回任务的唯一标识 ID"""
        ...

    @property
    def done(self) -> bool:
        """read-only, 返回任务是否完成"""
        ...

    @classmethod
    def get(cls, task_id: str) -> Optional["Task"]:
        """类方法，根据任务 ID 获取任务实例"""
        ...

    @classmethod
    def create(cls, task_runner: TaskRunner) -> "Task":
        """类方法，创建任务实例"""
        ...

    @classmethod
    def destroy(cls) -> None:
        """类方法，销毁所有任务实例"""
        ...
