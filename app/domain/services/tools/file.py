from typing import Optional

from app.domain.external.sandbox import Sandbox
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseToolSet, tool


class FileTool(BaseToolSet):
    """文件工具箱"""

    name: str = "file"

    def __init__(self, sandbox: Sandbox) -> None:
        super().__init__()
        self.sandbox = sandbox

    @tool(
        name="read_file",
        description="读取沙箱中指定路径的文件内容，可指定行范围、读取长度上限以及是否使用 sudo",
        parameters={
            "filepath": {
                "type": "string",
                "description": "目标文件的绝对路径",
            },
            "start_line": {
                "type": "integer",
                "description": "（可选）起始行号（从 0 开始），不传则从文件开头读取",
            },
            "end_line": {
                "type": "integer",
                "description": "（可选）结束行号（不含），不传则读取到文件末尾",
            },
            "sudo": {
                "type": "boolean",
                "description": "（可选）是否使用 sudo 权限读取，默认为 false",
            },
            "max_length": {
                "type": "integer",
                "description": "（可选）返回内容的最大字符数，默认 10000",
            },
        },
        required=["filepath"],
    )
    async def read_file(
        self,
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        sudo: Optional[bool] = False,
        max_length: Optional[int] = 10000,
    ) -> ToolResult:
        """传递文件路径读取沙箱中的文件内容"""
        return await self.sandbox.read_file(
            filepath=filepath,
            start_line=start_line,
            end_line=end_line,
            sudo=sudo,
            max_length=max_length,
        )

    @tool(
        name="write_file",
        description="根据传递的路径和内容往沙箱中写入数据，可控制追加模式与首尾换行",
        parameters={
            "filepath": {
                "type": "string",
                "description": "目标文件的绝对路径",
            },
            "content": {
                "type": "string",
                "description": "要写入文件的文本内容",
            },
            "append": {
                "type": "boolean",
                "description": "（可选）是否为追加模式，true 时在文件末尾追加，否则覆盖整个文件",
            },
            "leading_newline": {
                "type": "boolean",
                "description": "（可选）是否在内容开头添加一个换行符，默认为 false",
            },
            "trailing_newline": {
                "type": "boolean",
                "description": "（可选）是否在内容末尾添加一个换行符，默认为 false",
            },
            "sudo": {
                "type": "boolean",
                "description": "（可选）是否使用 sudo 权限写入，默认为 false",
            },
        },
        required=["filepath", "content"],
    )
    async def write_file(
        self,
        filepath: str,
        content: str,
        append: Optional[bool] = False,
        leading_newline: Optional[bool] = False,
        trailing_newline: Optional[bool] = False,
        sudo: Optional[bool] = False,
    ) -> ToolResult:
        """根据传递的路径和内容往沙箱中写入数据"""
        return await self.sandbox.write_file(
            filepath=filepath,
            content=content,
            append=append,
            leading_newline=leading_newline,
            trailing_newline=trailing_newline,
            sudo=sudo,
        )

    @tool(
        name="replace_in_file",
        description="根据路径 + 旧文本 + 新文本，替换沙箱文件中首次匹配的字符串",
        parameters={
            "filepath": {
                "type": "string",
                "description": "目标文件的绝对路径",
            },
            "old_str": {
                "type": "string",
                "description": "要被替换的原文本",
            },
            "new_str": {
                "type": "string",
                "description": "用于替换的新文本",
            },
            "sudo": {
                "type": "boolean",
                "description": "（可选）是否使用 sudo 权限修改，默认为 false",
            },
        },
        required=["filepath", "old_str", "new_str"],
    )
    async def replace_in_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        sudo: Optional[bool] = False,
    ) -> ToolResult:
        """根据传递的路径+要替换的文本+替换的文本替换沙箱中的文件"""
        return await self.sandbox.replace_in_file(
            filepath=filepath, old_str=old_str, new_str=new_str, sudo=sudo
        )

    @tool(
        name="search_in_file",
        description="在指定文件中按正则表达式搜索匹配的内容",
        parameters={
            "filepath": {
                "type": "string",
                "description": "目标文件的绝对路径",
            },
            "regex": {
                "type": "string",
                "description": "用于匹配内容的正则表达式",
            },
            "sudo": {
                "type": "boolean",
                "description": "（可选）是否使用 sudo 权限搜索，默认为 false",
            },
        },
        required=["filepath", "regex"],
    )
    async def search_in_file(
        self,
        filepath: str,
        regex: str,
        sudo: Optional[bool] = False,
    ) -> ToolResult:
        return await self.sandbox.search_in_file(filepath=filepath, regex=regex, sudo=sudo)

    @tool(
        name="find_files",
        description="在指定目录下按 glob 模式查找文件路径",
        parameters={
            "dir_path": {
                "type": "string",
                "description": "要搜索的目录绝对路径",
            },
            "glob_pattern": {
                "type": "string",
                "description": "用于匹配文件名的 glob 模式，例如 '**/*.py'",
            },
        },
        required=["dir_path", "glob_pattern"],
    )
    async def find_files(self, dir_path: str, glob_pattern: str) -> ToolResult:
        return await self.sandbox.find_files(
            dir_path=dir_path, glob_pattern=glob_pattern
        )

    @tool(
        name="list_files",
        description="列出指定目录下的文件和子目录",
        parameters={
            "dir_path": {
                "type": "string",
                "description": "目标目录的绝对路径",
            },
        },
        required=["dir_path"],
    )
    async def list_files(self, dir_path: str) -> ToolResult:
        return await self.sandbox.list_files(dir_path=dir_path)
