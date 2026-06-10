from typing import Protocol, Optional

from app.domain.models.tool_result import ToolResult


class Browser(Protocol):
    """浏览器服务扩展，涵盖：访问页面、URL跳转、输入框数据填充、移动鼠标、滚动页面、截图"""

    async def view_page(self) -> ToolResult:
        """获取当前浏览器页面的内容源码"""
        ...

    async def navigate(self, url: str) -> ToolResult:
        """传递对应的 url,使用浏览器导航到指定页面"""
        ...

    async def restart(self, url: str) -> ToolResult:
        """重启浏览器，导航到指定URL"""
        ...

    async def click(
        self,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """传递对应的元素索引或者 x,y 坐标实现点击功能"""
        ...

    async def input(
        self,
        text: str,
        press_enter: bool,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """传递对应的元素索引或者 x,y 坐标实现输入框数据填充"""
        ...

    async def move_mouse(
        self,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """传递xy坐标，移动鼠标"""
        ...

    async def press_key(self, key: str) -> ToolResult:
        """传递按键标识 Enter/Control+C 等实现浏览器模拟按键"""
        ...

    async def select_option(self, index: int, option: int) -> ToolResult:
        """传递索引+选项序号标识在下拉菜单中选择指定的选项"""
        ...

    async def scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """向上滚动浏览器，如果没传递 to_top=True, 则向上滚动一页，否则直接滚动到顶部"""
        ...

    async def scroll_down(self, to_bottom: Optional[bool] = None) -> ToolResult:
        """向下滚动浏览器，如果没传递 to_bottom=True, 则向下滚动一页，否则直接滚动到底部"""
        ...

    async def screenshot(self, full_page: Optional[bool] = None) -> bytes:
        """截取当前浏览器页面的截图,传递 full_page=True 则截取整个页面"""
        ...

    async def console_exec(self, javascript: str) -> ToolResult:
        """传递对应的js脚本在浏览器的当前页面控制台执行"""
        ...

    async def console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """传递最大输出行数，获取控制台的输出结果，如果不传递则获取所有输出"""
        ...