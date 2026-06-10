from typing_extensions import Optional

from app.domain.external.browser import Browser
from app.domain.models.tool_result import ToolResult

from .base import BaseToolSet, tool


class BrowserToolSet(BaseToolSet):
    """浏览器工具集"""

    name: str = "browser"

    def __init__(self, browser: Browser) -> None:
        super().__init__()
        self.browser = browser

    @tool(
        name="browser_view",
        description="查看当前浏览器页面内容，用于确认已打开页面的最新状态",
        parameters={},
        required=[],
    )
    async def browser_view(self) -> ToolResult:
        """获取浏览器当前网页内容并返回"""
        return await self.browser.view_page()

    @tool(
        name="browser_navigate",
        description="将浏览器导航至指定网址，当需要访问新页面时使用",
        parameters={
            "url": {
                "type": "string",
                "description": "要访问的完整URL,必需包含协议前缀（例如：https://）",
            }
        },
        required=["url"],
    )
    async def browser_navigate(self, url: str) -> ToolResult:
        """导航到指定URL"""
        return await self.browser.navigate(url)

    @tool(
        name="browser_restart",
        description="重启浏览器并导航到指定URL，当需要重置浏览器时使用",
        parameters={
            "url": {
                "type": "string",
                "description": "要访问的完整URL,必需包含协议前缀（例如：https://）",
            }
        },
        required=["url"],
    )
    async def browser_restart(self, url: str) -> ToolResult:
        """重启浏览器并导航到指定URL"""
        return await self.browser.restart(url)

    @tool(
        name="browser_click",
        description="点击当前页面中的元素，在需要点击页面元素时使用",
        parameters={
            "index": {
                "type": "integer",
                "description": "（可选）需要点击的元素索引",
            },
            "coordinate_x": {
                "type": "number",
                "description": "（可选）点击位置的 x 坐标",
            },
            "coordinate_y": {
                "type": "number",
                "description": "（可选）点击位置的 y 坐标",
            },
        },
        required=[],
    )
    async def browser_click(
        self,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """点击指定元素"""
        return await self.browser.click(index, coordinate_x, coordinate_y)

    @tool(
        name="browser_input",
        description="覆盖浏览器当前页面可编辑区域的文本（input/textarea输入框），在需要填充输入",
        parameters={
            "text": {
                "type": "string",
                "description": "要填充的文本内容",
            },
            "press_enter": {
                "type": "boolean",
                "description": "是否在输入完成后按下回车键",
            },
            "index": {
                "type": "integer",
                "description": "（可选）需要填充文本的元素索引",
            },
            "coordinate_x": {
                "type": "number",
                "description": "（可选）需要填充文本元素的 x 坐标",
            },
            "coordinate_y": {
                "type": "number",
                "description": "（可选）需要填充文本元素的 y 坐标",
            },
        },
        required=["text", "press_enter"],
    )
    async def browser_input(
        self,
        text: str,
        press_enter: bool,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """输入框数据填充"""
        return await self.browser.input(
            text, press_enter, index, coordinate_x, coordinate_y
        )

    @tool(
        name="browser_move_mouse",
        description="将鼠标光标移动至当前浏览器页面的指定位置，用于模拟用户的鼠标移动",
        parameters={
            "coordinate_x": {
                "type": "number",
                "description": "目标光标位置的 x 坐标",
            },
            "coordinate_y": {
                "type": "number",
                "description": "目标光标位置的 y 坐标",
            },
        },
        required=["coordinate_x", "coordinate_y"],
    )
    async def browser_move_mouse(
        self,
        coordinate_x: float,
        coordinate_y: float,
    ) -> ToolResult:
        """移动鼠标到指定位置"""
        return await self.browser.move_mouse(coordinate_x, coordinate_y)

    @tool(
        name="browser_press_key",
        description="在当前浏览器页面模拟按键，当需要指定特定的键盘操作时使用。",
        parameters={
            "key": {
                "type": "string",
                "description": "要模拟的按键名称（例如：Enter、Tab、ArrowUp），支持组合键（例如：Ctrl+A）",
            },
        },
        required=["key"],
    )
    async def browser_press_key(self, key: str) -> ToolResult:
        """按下指定键"""
        return await self.browser.press_key(key)

    @tool(
        name="browser_select_option",
        description="从当前浏览器页面的下拉列表元素中选择指定选项，用于选择下拉菜单中的选项",
        parameters={
            "index": {
                "type": "integer",
                "description": "需要操作的下拉列表元素的索引（序号）",
            },
            "option": {
                "type": "integer",
                "description": "需要选择的选项序号，从0开始(注：指下拉框里的第几项)",
            },
        },
        required=["index", "option"],
    )
    async def browser_select_option(self, index: int, option: int) -> ToolResult:
        """在下拉菜单中选择指定的选项"""
        return await self.browser.select_option(index, option)

    @tool(
        name="browser_scroll_up",
        description="向上滚动浏览器页面，用于查看上方内容或返回页面顶部",
        parameters={
            "to_top": {
                "type": "boolean",
                "description": "（可选）是否直接滚动到页面顶部，而非向上滚动一屏。",
            },
        },
        required=["to_top"],
    )
    async def browser_scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """向上滚动浏览器，如果没传递 to_top=True, 则向上滚动一页，否则直接滚动到顶部"""
        return await self.browser.scroll_up(to_top)

    @tool(
        name="browser_scroll_down",
        description="向下滚动浏览器页面，用于查看下方内容或滚动到底部。",
        parameters={
            "to_down": {
                "type": "boolean",
                "description": "（可选）是否直接滚动到页面底部，而非向下滚动一屏。",
            },
        },
        required=["to_down"],
    )
    async def browser_scroll_down(self, to_down: Optional[bool] = None) -> ToolResult:
        """向下滚动浏览器，如果没传递 to_down=True, 则向下滚动一页，否则直接滚动到底部"""
        return await self.browser.scroll_down(to_down)

    @tool(
        name="browser_screenshot",
        description="截取当前浏览器页面的截图",
        parameters={
            "full_page": {
                "type": "boolean",
                "description": "（可选）是否截取整个页面，默认为 False 即截取当前可见区域。",
            },
        },
        required=["full_page"],
    )
    async def browser_screenshot(self, full_page: Optional[bool] = None) -> bytes:
        """截取当前浏览器页面的截图,传递 full_page=True 则截取整个页面"""
        return await self.browser.screenshot(full_page)

    @tool(
        name="browser_console_exec",
        description="在浏览器控制台中执行 JavaScript 代码，当需要指定自定义脚本时使用",
        parameters={
            "javascript": {
                "type": "string",
                "description": "要指定的JavaScript代码，请注意运行时环境为浏览器控制台",
            },
        },
        required=["javascript"],
    )
    async def browser_console_exec(self, javascript: str) -> ToolResult:
        """在浏览器的当前页面控制台执行指定的js脚本"""
        return await self.browser.console_exec(javascript)

    @tool(
        name="browser_console_view",
        description="查看浏览器控制台输出，用于检查 JavaScript 日志或调试页面错误。",
        parameters={
            "max_lines": {
                "type": "integer",
                "description": "（可选）返回的日志最大行数。",
            },
        },
        required=["max_lines"],
    )
    async def browser_console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """查看浏览器当前页面的控制台输出"""
        return await self.browser.console_view(max_lines)
