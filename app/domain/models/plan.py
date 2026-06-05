import uuid
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

class ExecutionSatus(str, Enum):
    """规划/任务执行的状态"""

    PENDING = "pending"  # 空闲 or 等待中
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed" # 执行失败


class Step(BaseModel):
    """计划中的每一个步骤/子任务"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 子任务id
    description: str = ""  # 步骤的描述信息
    status: ExecutionSatus = ExecutionSatus.PENDING  # 子任务的执行状态
    result: Optional[str] = None  # 结果
    error: Optional[str] = None  # 错误信息
    success: bool = False  # 是否执行成功
    attachements: List[str] = Field(
        default_factory=list
    )  # 附件列表信息（存储的是虚拟机文件路径）

    @property
    def done(self) -> bool:
        """read-only, 返回步骤是否结束"""
        return self.status in [ExecutionSatus.COMPLETED, ExecutionSatus.FAILED]

class Plan(BaseModel):
    """规划Domain模型，用于存储用户传递消息拆分出来的子任务/子步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 计划id
    title: str = ""  # 任务标题
    goal: str = ""  # 任务目标
    language: str = ""  # 工作语言
    steps: List[Any] = Field(default_factory=list)  # 步骤列表/子任务列表
    message: str = ""  # 用户传递的消息
    status: ExecutionSatus = ExecutionSatus.PENDING  # 规划的状态
    error: Optional[str] = None  # 错误信息

    # todo: 未预留 result 用于记录规划的结果

    @property
    def done(self) -> bool:
        """read-only, 用于判断计划是否结束"""
        return self.status in [ExecutionSatus.COMPLETED, ExecutionSatus.FAILED]

    def get_next_step(self) -> Optional[Step]:
        """获取需要执行的下一个步骤"""
        return next( (step for step in self.steps if not step.done), None)

    