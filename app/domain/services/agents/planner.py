import logging
from typing import AsyncGenerator, Optional

from app.domain.models.event import (
    Event,
    MessageEvent,
    Plan,
    PlanEvent,
    PlanEventStatus,
)
from app.domain.models.message import Message
from app.domain.models.plan import Step
from app.domain.services.prompts.planner import (
    CREATE_PLAN_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    UPDATE_PLAN_PROMPT,
)
from app.domain.services.prompts.system import SYSTEM_PROMPT

from .base import BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """规划智能体，将用户的需求/任务拆解成多个子步骤"""

    name: str = "planner"
    _system_prompt: str = SYSTEM_PROMPT + "\n\n" + PLANNER_SYSTEM_PROMPT
    _format: Optional[str] = "json_schema"
    _tool_choice: Optional[str] = "none"

    async def create_plan(self, message: Message) -> AsyncGenerator[Event, None]:
        """根據用戶傳遞的消息创建计划/规划，迭代返回对应的事件"""
        # 1.根据用户传递的消息生成创建 Plan 的提示词
        query = CREATE_PLAN_PROMPT.format(
            message=message.message, attachments="\n".join(message.attachments)
        )

        # 调用 invoke 方法返回迭代事件
        async for event in self.invoke(query=query):
            # 规划智能体因为使用 json_object 格式，正常情况下会返回一个 MessageEvent
            if isinstance(event, MessageEvent):
                # 解析 MessageEvent 中的消息内容，返回对应的事件
                logger.info(f"PlannerAgent 生成的消息：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 将解析对象转换为 Plan 计划
                plan = Plan.model_validate(parsed_obj)

                # 6. 返回 PlanEvent 表示规划创建成功
                yield PlanEvent(plan=plan)
                # 这里为什么不 return 
            else:
                # 返回的不是 MessageEvent 的事件
                yield event

    async def update_plan(
        self, 
        plan: Plan,
        step: Step
    ) -> AsyncGenerator[Event, None]:
        """根据传递的原始 Plan 和 Step 更新事件"""
        # 1.创建更新 Plan 的提示词
        query = UPDATE_PLAN_PROMPT.format(
            plan=plan.model_dump_json(),
            step=step.model_dump_json(),
        )

        # 2.调用 invoke 方法返回迭代事件
        async for event in self.invoke(query=query):
            # 3.判断生成是不是 MessageEvent
            if isinstance(event, MessageEvent):
                logger.info(f"PlannerAgent 生成的消息：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                # 将解析对象转为 Plan 对象
                update_plan = Plan.model_validate(parsed_obj)

                # 拷贝更新计划中的 steps,避免造成数据污染
                new_steps = [Step.model_validate(step) for step in update_plan.steps]

                # 查询旧计划中第一个未完成的任务
                first_pending_index = None
                for idx, step in enumerate(plan.steps):
                    if not step.done:
                        first_pending_index = idx
                        break

                # 判断是否有未完成的步骤，如果有则执行更新
                if first_pending_index is not None:
                    # 9.获取历史已经完成的步骤并更新
                    updated_steps = plan.steps[:first_pending_index]
                    updated_steps.extend(new_steps)

                    # 更新 plan
                    plan.steps = updated_steps

                # 返回规划更新事件
                yield PlanEvent(plan=plan, status=PlanEventStatus.UPDATED)
            else:
                yield event
