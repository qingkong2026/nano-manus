from typing import Optional

from app.domain.models.tool_result import ToolResult

from .base import BaseToolSet, tool

from app.domain.external.sandbox import Sandbox

class ShellToolSet(BaseToolSet):
    """Shell 工具箱，提供 Shell 交互功能"""

    name: str = "shell"

    def __init__(
        self,
        sandbox: Sandbox
    ):
        super().__init__()
        self.sandbox = sandbox


    @tool(
        name="shell_exec",
        description="在指定 Shell 命令中执行命令。可用于运行代码，安装依赖包或文件管理",
        parameters={
            "session_id": {
                "type": "string",
                "description": "目标Shell 会话的唯一标识",
            },
            "exec_dir": {
                "type": "string",
                "description": "执行命令的工作目录（必须使用绝对路径）",
            },
            "command": {
                "type": "string",
                "description": "要执行的 Shell 命令",
            },
        },
        required=["session_id", "exec_dir", "command"],
    )
    async def shell_exec(
        self, session_id: str, exec_dir: str, command: str
    ) -> ToolResult:
        """执行脚本"""
        return await self.sandbox.exec_command(session_id=session_id, exec_dir=exec_dir,command=command)
    

    @tool(
        name="shell_view",
        description="根据会话id查看指定 Shell 会话中最近一次命令执行的输出结果",
        parameters={
            "session_id": {
                "type": "string",
                "description": "目标Shell 会话的唯一标识",
            },
        },
        required=["session_id"],
    )
    async def shell_view(self, session_id: str) -> ToolResult:
        """根据会话id查看shell执行结果"""
        return await self.sandbox.view_shell(session_id=session_id)

    @tool(
        name="shell_wait",
        description="等待指定 Shell 会话中正在运行的进程返回，可指定最长等待秒数",
        parameters={
            "session_id": {
                "type": "string",
                "description": "目标Shell 会话的唯一标识",
            },
            "seconds": {
                "type": "integer",
                "description": "最长等待秒数，默认为 None 表示使用默认超时",
            },
        },
        required=["session_id"],
    )
    async def shell_wait(self, session_id: str, seconds: Optional[int] = None) -> ToolResult:
        """等待指定 Shell 会话中正在运行的进程返回"""
        return await self.sandbox.wait_for_process(session_id=session_id, seconds=seconds)


    @tool(
        name="shell_write_to_process",
        description="向指定 Shell 会话中正在运行的进程写入输入文本，可选择是否按下回车",
        parameters={
            "session_id": {
                "type": "string",
                "description": "目标Shell 会话的唯一标识",
            },
            "input_text": {
                "type": "string",
                "description": "要写入到进程标准输入的文本",
            },
            "press_enter": {
                "type": "boolean",
                "description": "写入后是否按下回车键提交输入",
            },
        },
        required=["session_id", "input_text", "press_enter"],
    )
    async def shell_write_to_process(
        self,
        session_id: str,
        input_text: str,
        press_enter: bool,
    ) -> ToolResult:
        """向指定 Shell 会话正在运行的进程写入输入文本"""
        return await self.sandbox.write_to_process(session_id=session_id, input_text=input_text, press_enter=press_enter)


    @tool(
        name="shell_kill_process",
        description="终止指定 Shell 会话中正在运行的进程",
        parameters={
            "session_id": {
                "type": "string",
                "description": "目标Shell 会话的唯一标识",
            },
        },
        required=["session_id"],
    )
    async def shell_kill_process(self, session_id: str) -> ToolResult:
        """在指定 Shell 会话中终止正在运行的进程"""
        return await self.sandbox.kill_process(session_id=session_id)
    
