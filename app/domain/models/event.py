import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.domain.models.file import File
from app.domain.models.plan import Plan, Step
from app.domain.models.tool_result import ToolResult


class PlanEventStatus(str, Enum):
    """规划事件状态枚举"""

    CREATED = "created"  # 已创建
    UODATED = "updated"  # 已更新
    COMPLETED = "completed"  # 已完成


class StepEventStatus(str, Enum):
    """步骤事件状态"""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolEventStatus(str, Enum):
    """工具事件状态类型枚举"""

    CALLING = "calling"  # 调用中
    CALLED = "called"  # 调用完毕


class BaseEvent(BaseModel):
    """基础事件类型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 事件id
    type: Literal[""] = ""  # 事件的类型
    created_at: datetime = Field(default_factory=datetime.now)  # 事件创建的时间


class PlanEvent(BaseEvent):
    """规划事件类型"""

    type: Literal["plan"] = "plan"
    plan: Plan
    status: PlanEventStatus = PlanEventStatus.CREATED  # 规划事件状态


class TitleEvent(BaseEvent):
    """标题事件类型"""

    type: Literal["title"] = "title"
    title: str = ""


class StepEvent(BaseEvent):
    """子任务/步骤事件类型"""

    type: Literal["step"] = "step"
    step: Step  # 步骤信息
    status: StepEventStatus = StepEventStatus.STARTED


class MessageEvent(BaseEvent):
    """消息事件类型，包含人类消息和AI消息"""

    type: Literal["message"] = "message"
    role: Literal["user", "assistant"] = "assistant"
    message: str = ""  # 消息本身
    attachements: List[File] = Field(default_factory=list)  # 附件列表信息


class BrowserToolOuput(BaseModel):
    """浏览器工具扩展内容"""

    screenshot: str  # 浏览器扩展截图


class MCPToolOuput(BaseModel):
    """MCP工具内容"""

    result: Any


# todo: 更多工具扩展内容
ToolOutput = Union[BrowserToolOuput, MCPToolOuput]


class ToolEvent(BaseEvent):
    """工具事件类型"""

    # todo:工具事件等待工具模块接入后完善
    type: Literal["tool"] = "tool"
    tool_use_id: str  # 工具调用 Id
    tool_set_name: str  # 工具箱名字
    tool_name: str  # 工具名字/LLM调用函数

    tool_input: Dict[str, Any]  # LLM 生成的工具调用参数

    tool_output: Optional[ToolOutput] = None  # 工具结构化扩展输出
    tool_result: Optional[ToolResult] = None  # 工具调用结果

    status: ToolEventStatus = ToolEventStatus.CALLING  # 工具事件状态


class WaitEvent(BaseEvent):
    """等待事件类型，等待用户输入确认"""

    type: Literal["wait"] = "wait"


class ErrorEvent(BaseModel):
    """错误事件类型"""

    tyep: Literal["error"] = "error"
    error: str = ""


class DoneEvent(BaseModel):
    """结束事件类型"""

    type: Literal["done"] = "done"


# 定义应用事件类型声明
Event = Union[
    PlanEvent,
    TitleEvent,
    StepEvent,
    MessageEvent,
    ToolEvent,
    WaitEvent,
    ErrorEvent,
    DoneEvent,
]
