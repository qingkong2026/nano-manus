from typing import AsyncGenerator, Optional
from venv import logger

from app.domain.models.file import File
from app.domain.models.event import ErrorEvent, Event, MessageEvent, StepEvent, StepEventStatus, ToolEvent, ToolEventStatus, WaitEvent
from app.domain.models.message import Message
from app.domain.models.plan import ExecutionStatus, Plan, Step

from .base import BaseAgent
from app.domain.services.prompts.system import SYSTEM_PROMPT
from app.domain.services.prompts.react import EXECUTION_PROMPT, REACT_SYSTEM_PROMPT, SUMMARIZE_PROMPT

class ReActAgent(BaseAgent):
    """基于 ReAct 架构的执行 Agent"""

    name: str = "react"
    _system_prompt: str = SYSTEM_PROMPT + REACT_SYSTEM_PROMPT
    _format: Optional[str] = "json_schema"

    async def execute_step(self, plan: Plan, step: Step, message: Message) -> AsyncGenerator[Event, None]:
        """根据传递的消息+规划+子步骤，执行相应的子步骤"""
        # 1.根据传递的内容生成执行消息
        query = EXECUTION_PROMPT.format(
            message=message.message,
            attachments="\n".join(message.attachments),
            language=plan.language,
            step=step.description,
        )

        # 2.更新步骤的执行状态为运行中并返回 Step 事件
        step.status = ExecutionStatus.RUNNING
        yield StepEvent(step=step, status=StepEventStatus.STARTED)

        # 3.调用 invoke 获取 agent 返回的事件类型
        async for event in self.invoke(query=query):
            # 4.根据事件类型更新步骤状态并返回相应事件
            if isinstance(event, ToolEvent):
                if event.tool_name == "message_ask_user":
                    # 如果工具在调用中，则需要返回一条消息告知用户需要处理什么
                    if event.status == ToolEventStatus.CALLING:
                        yield MessageEvent(
                            role="assistant",
                            # todo:由于 message_ask_user 工具还没实现，所以参数未定，暂定为 text
                            message=event.tool_input.get("text","")
                        )
                    elif event.status == ToolEventStatus.CALLED:
                        # 如果工具事件为已调用，则需要返回等待事件并中断程序
                        yield WaitEvent()
                        return
            elif isinstance(event, MessageEvent):
                step.status = ExecutionStatus.COMPLETED

                parsed_obj = await self._json_parser.invoke(event.message)
                new_step = Step.model_validate(parsed_obj)

                # 10.更新子步骤的数据
                step.success = new_step.success
                step.result = new_step.result
                step.attachments = new_step.attachments

                # 11.返回步骤完成事件
                yield StepEvent(step=step, status=StepEventStatus.COMPLETED)

                # 12.如果子步骤拿到结果，还需要返回一段消息给用户（将结果返回给用户）
                if step.result:
                    yield MessageEvent(role="assistant", message=step.result)
                # todo: 为什么这里不直接 return
                continue
            elif isinstance(event, ErrorEvent):
                # 13.错误事件更新步骤的状态
                step.status = ExecutionStatus.FAILED
                step.error = event.error

                # 14.返回子步骤对应事件
                yield StepEvent(step=step, status=StepEventStatus.FAILED)

            # 15.其他场景将事件直接返回
            yield event

    async def summarize(self) -> AsyncGenerator[Event, None]:
        """调用Agent汇总历史的消息并生成最终回复+附件"""
        # 1.构建请求 query
        query = SUMMARIZE_PROMPT

        # 2.调用 invoke 方法获取 Agent 生成的事件
        async for event in self.invoke(query=query):
            # 3.判断事件类型是否为 MessageEvent, 如果是则表示 Agent 结构化生成汇总内容
            if isinstance(event, MessageEvent):
                # 4.记录日志并解析输出内容
                logger.info(f"执行Agent生成汇总内容：{event.message}")
                parsed_obj = await self._json_parser.invoke(event.message)

                message = Message.model_validate(parsed_obj)

                # 提取消息中的附件消息
                attachments = [File(filepath=filepath) for filepath in message.attachments]
 
                yield MessageEvent(
                    role="assistant",
                    message=message.message,
                    attachments=attachments
                )
            else:
                yield event









    
