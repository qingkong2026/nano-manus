import asyncio
import logging
import uuid
from typing import Dict, Optional

from app.domain.external.message_queue import MessageQueue
from app.domain.external.task import Task, TaskRunner
from app.infrastructure.external.message_queue import (
    RedisMessageQueue,
)

logger = logging.getLogger(__name__)


class RedisStreamTask(Task):
    """基于Redis Stream的任务类"""

    # 定义一个全局变量用于存储所有已经注册的任务
    _task_registry: Dict[str, "RedisStreamTask"] = {}

    def __init__(self, task_runner: TaskRunner) -> None:
        """构造函数，传递任务运行器完成 Task 初始化"""
        self._task_runner = task_runner
        self._id = str(uuid.uuid4())
        self._execution_task: Optional[asyncio.Task] = None  # 定义后台执行的任务

        input_stream_name = f"task:input:{self._id}"
        output_stream_name = f"task:output:{self._id}"

        self._input_stream = RedisMessageQueue(input_stream_name)
        self._output_stream = RedisMessageQueue(output_stream_name)

        # 将当前任务注册到全局任务注册表中
        RedisStreamTask._task_registry[self._id] = self

    def _cleanup_registry(self) -> None:
        """清除类全局变量中当前任务的注册信息"""
        if self._id in RedisStreamTask._task_registry:
            del RedisStreamTask._task_registry[self._id]
            logger.info(f"任务[{self._id}]从任务注册表中移除")

    async def _on_task_done(self) -> None:
        """任务结束时的回调函数"""
        # 1.检测 task_runner 是否存在，如果存在则调用 task_runner 的回调函数
        try:
            if self._task_runner:
                await asyncio.create_task(self._task_runner.on_done(self))
        finally:
            # 2. 清除当前任务对应的资源
            self._cleanup_registry()

    async def _execute_task(self) -> None:
        """使用 TaskRunner 来执行任务"""
        try:
            await self._task_runner.execute(self)
        except asyncio.CancelledError:
            logger.info(f"任务[{self._id}]执行被取消")
        except Exception as e:
            logger.error(f"任务[{self._id}]执行出现异常：{str(e)}")
        finally:
            await self._on_task_done()

    async def run(self) -> None:
        """使用提供的 task_runner 来执行任务"""
        # 1.任务已经结束 或者 任务正在执行，直接返回
        if self._execution_task is not None:
            logger.warning(f"任务[{self._id}]已经结束或正在执行，忽略重复启动")
            return

        # 2.创建后台任务
        self._execution_task = asyncio.create_task(self._execute_task())
        logger.info(f"任务[{self._id}]后台开始执行...")

    def cancel(self) -> bool:
        """取消当前执行的任务"""
        if self.done:
            # 1.任务已经结束，清除任务注册表中的记录
            return False
        # 2.任务正在执行
        self._execution_task.cancel()
        logger.info(f"任务[{self._id}]已经标记取消")
        return True

    @property
    def input_stream(self) -> MessageQueue:
        return self._input_stream

    @property
    def output_stream(self) -> MessageQueue:
        return self._output_stream

    @property
    def id(self) -> str:
        return self._id

    @property
    def done(self) -> bool:
        if self._execution_task is None:
            return False
        return self._execution_task.done()

    @classmethod
    def get(cls, task_id: str) -> Optional["Task"]:
        return RedisStreamTask._task_registry.get(task_id)

    @classmethod
    def create(cls, task_runner: TaskRunner) -> "Task":
        return cls(task_runner)

    @classmethod
    async def destroy(cls) -> None:

        # 1.复制一份 key 列表，防止遍历时字典变化导致异常
        task_ids = list(RedisStreamTask._task_registry.keys())

        # 2.遍历任务列表，取消任务并销毁执行器
        for task_id in task_ids:
            # 获取对应的任务
            task = RedisStreamTask._task_registry[task_id]
            # 取消任务
            task.cancel()

        # 3.等待所有任务真正结束
        for task_id in task_ids:
            task = RedisStreamTask._task_registry[task_id]
            if task and task._execution_task:
                try:
                    await task._execution_task
                except Exception:
                    pass

            # # 2.检测任务是否有任务执行器
            # if task._task_runner:
            #     await task._task_runner.destroy()

        # 4.清除任务注册表中的全部任务
        cls._task_registry.clear()
