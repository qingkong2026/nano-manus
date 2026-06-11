import asyncio
import logging
from socket import timeout
from typing import Any, List, Optional

from markdownify import markdownify
from playwright.async_api import Browser, Page, Playwright, async_playwright

from app.domain.external.browser import Browser as BrowserProtocol
from app.domain.external.llm import LLM
from app.domain.models.memory import MessageRole, UniformMessage, UniformTextBlock
from app.domain.models.tool_result import ToolResult
from app.infrastructure.external.browser.playwright_browser_fun import (
    GET_INTERACTIVE_ELEMENT_FUNC,
    GET_VISIBLE_CONTENT_FUNC,
)

logger = logging.getLogger(__name__)


class PlaywrightBrowser(BrowserProtocol):
    """基于 Playwright 管理的浏览器扩展"""

    def __init__(
        self,
        cdp_url: str,
        llm: Optional[LLM] = None,
    ) -> None:
        self.llm: Optional[LLM] = llm
        self.cdp_url: str = cdp_url
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def _ensure_browser(self) -> None:
        """确保浏览器存在，如果不存在则初始化"""
        if not self.browser or not self.page:
            is_initialized = await self.initialize()
            if not is_initialized:
                raise Exception("Failed to Initialize Playwright Browser")

    async def _ensure_page(self) -> None:
        """确保浏览器页面存在，如果不存在则新建"""
        await self._ensure_browser()

        # 1.如果页面不存在则创建上下文+页面
        if not self.page:
            self.page = await self.browser.new_page()
        else:
            contexts = self.browser.contexts
            if contexts:
                default_context = contexts[0]
                pages = default_context.pages

                # 判断页面是否存在
                if pages:
                    # 获取当前最新的页面
                    latest_page = pages[-1]
                    if self.page != latest_page:
                        self.page = latest_page

    async def wait_for_page_load(self, timeout: int = 15) -> bool:
        """传递超时时间，等待当前页面是否加载完毕"""
        # 1.确保当前页面存在
        await self._ensure_page()

        # 使用异步任务事件循环中的时间作为开始时间（只和异步任务相关）
        start_time = asyncio.get_event_loop().time()
        check_interval = 5

        # 3.循环检测网页是否加载成功
        while asyncio.get_event_loop().time() - start_time < timeout:
            # 使用 js 代码判断网页是否加载成功
            is_completed = await self.page.evaluate(
                """() => document.readyState === 'complete'"""
            )
            if is_completed:
                return True

            # 未加载成功则休眠对面时间
            await asyncio.sleep(check_interval)

        return False

    async def navigate(self, url: str) -> ToolResult:
        """根据传递的 url 跳转到指定页面"""
        # 1.确保页面存在
        await self._ensure_page()

        try:
            # 1.在跳转之前先将可交互元素的缓存清空
            self.interactive_elements_cache = []

            # 使用 goto 进行跳转
            await self.page.goto(url)
            return ToolResult(
                success=True,
                data={"interactive_elements": self._extract_interactive_elements()},
            )

        except Exception as e:
            return ToolResult(success=False, message=f"浏览器导航到{url}失败")

    async def view_page(self) -> ToolResult:
        """获取当前页面的内容（内容+可交互元素）"""
        # 1.确保页面存在
        await self._ensure_page()

        # 2.等待页面加载完成
        await self.wait_for_page_load()

        # 3.更新页面的可交互元素
        interactive_elements = await self._extract_interactive_elements()
        content = await self._extract_content()

        # 4.返回工具结果
        return ToolResult(
            success=True,
            data={"content": content, "interactive_elements": interactive_elements},
        )

    async def restart(self, url: str) -> ToolResult:
        """重启并跳转到指定 URL"""
        await self.cleanup()
        return await self.navigate(url)

    async def scroll_up(self, to_top: Optional[bool] = None) -> ToolResult:
        """向上滚动浏览器一个屏幕或者到最页面顶部"""
        await self._ensure_page()

        if to_top:
            await self.page.evaluate("window.scrollTo(0,0)")
        else:
            await self.page.evaluate("window.scrollTo(0, -window.innerHeight)")

        return ToolResult(success=True)

    async def scroll_down(self, to_down: Optional[bool] = None) -> ToolResult:
        """向下滚动浏览器一个屏幕或者到页面最底部"""
        await self._ensure_page()

        if to_down:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight)")

        return ToolResult(success=True)

    async def screenshot(self, full_page: Optional[bool] = None) -> bytes:
        """传递 full_page 完成页面截图"""
        await self._ensure_page()

        # 创建一个截图配置
        screenshot_options = {"full_page": full_page, "type": "png"}

        return await self.page.screenshot(**screenshot_options)

    async def console_exec(self, javascript: str) -> ToolResult:
        """传递 js 代码在当前页面控制台执行"""
        await self._ensure_page()
        result = await self.page.evaluate(javascript)
        return ToolResult(success=True, data={"result": result})

    async def console_view(self, max_lines: Optional[int] = None) -> ToolResult:
        """根据传递的行数查看控制台的日志"""
        await self._ensure_page()
        logs = await self.page.evaluate("""() => {
            return window.console.logs || [];
        }""")

        if max_lines is not None:
            logs = logs[-max_lines]

        return ToolResult(success=True, data={"logs": logs})

    async def initialize(self) -> bool:
        """初始化并确保资源是可用的"""
        # 1.定义最大重试次数
        max_retries = 3
        retry_interval = 1
        BLANK_PAGE_URLS = {
            "about:blank",
            "chrome://newtab",
            "chrome://new-tab-page/",
            "",
        }

        for attempt in range(max_retries):
            try:
                # 1.创建 playwright 上下文并连接到 cdp 浏览器
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    self.cdp_url
                )

                # 2.获取浏览器上下文
                contexts = self.browser.contexts

                # 如果上下文存在，并且第一个上下文只有一个页面
                if contexts and contexts[0].pages and len(contexts[0].pages) == 1:
                    page = contexts[0].pages[0]

                    # 判断当前页面是不是空页面，如果不是，则创建新的页面
                    if page.url in BLANK_PAGE_URLS:
                        self.page = page
                    else:
                        # 创建一个新的页面
                        self.page = await contexts[0].new_page()
                else:
                    # 上下文不存在或者页面不唯一则表示数据被污染，新建一个
                    context = await self.browser.new_context()
                    self.page = await context.new_page()

                logger.info("Playwright browser initialized successfully")
                return True
            except Exception as e:
                # 清除所有资源
                await self.cleanup()

                # 判断重试次数是否等于最大重试次数
                if attempt + 1 == max_retries:
                    logger.error(
                        f"Playwright initialization failed after {max_retries} retries: {str(e)}"
                    )
                    return False

                # 使用指数级进行休眠
                retry_interval = max(retry_interval * 2, 10)
                logger.warning(
                    f"Failed to initialize Playwright browser. Retrying attempt {attempt + 1}..."
                )
                await asyncio.sleep(retry_interval)

        return False

    async def cleanup(self) -> None:
        """清除Playwright资源，包含浏览器、页面、Playwright"""
        try:
            # 1.检查浏览器是否存在，如果存在则删除该浏览器下的所有 tabs 页面
            if self.browser:
                # 获取浏览器的所有上下文
                contexts = self.browser.contexts
                if contexts:
                    # 清理每个上下文的所有页面
                    for context in contexts:
                        pages = context.pages
                        for page in pages:
                            if not page.is_closed():
                                await page.close()

            # 判断 self.page 是否关闭
            if self.page and not self.page.is_closed():
                await self.page.close()

            # 判断 browser 是否关闭
            if self.browser:
                await self.browser.close()

            # 判断 playwright 是否关闭
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"清理Playwright浏览器资源出错：{str(e)}")
        finally:
            # 重置资源
            self.page = None
            self.browser = None
            self.playwright = None

    async def _extract_content(self) -> str:
        """提取当前页面的内容"""
        # 1.使用 js 代码获取当前页面可见元素内容
        visible_content = await self.page.evaluate(GET_VISIBLE_CONTENT_FUNC)

        # 2.使用 markdownify  这个库将 html 文档转换成 makrdown
        markdown_content = markdownify(visible_content)

        # 3.模型上下文有限，提取最大不超过 50k 个字符
        max_content_length = min(len(markdown_content), 50000)

        trimmed_content = markdown_content[:max_content_length]
        # 判断是否传递了 llm,如果传递了，使用 llm 进行整理
        if self.llm:
            messages: List[UniformMessage] = [
                UniformMessage(
                    role=MessageRole.SYSTEM,
                    content=[
                        UniformTextBlock(
                            text="你是一名专业的网页信息提取助手。请从当前页面内容中提取所有信息并将其转换为markdown格式。"
                        )
                    ],
                ),
                UniformMessage(
                    role=MessageRole.USER,
                    content=[UniformTextBlock(text=trimmed_content)],
                ),
            ]

            llm_resp: UniformMessage = await self.llm.invoke(messages)

            text_parts = []
            for block in llm_resp.content:
                if isinstance(block, UniformTextBlock) and block.text.strip():
                    text_parts.append(block.text)
            return "\n".join(text_parts)
        else:
            return trimmed_content

    async def _extract_interactive_elements(self) -> List[str]:
        """提取当前页面上的可交互元素"""

        # 1.确保页面存在
        await self._ensure_page()

        # 2.清除当前页面上的缓存可交互元素列表
        self.interactive_elements_cache = []

        # 3.执行 js 脚本获取可交互的元素列表
        interactive_elements = await self.page.evaluate(GET_INTERACTIVE_ELEMENT_FUNC)

        # 4.更新缓存的可交互元素列表
        self.interactive_elements_cache = interactive_elements

        # 5.格式化可交付元素为字符串
        formatted_elements = []
        for element in interactive_elements:
            formatted_elements.append(
                f"{element['index']}:<{element['tag']}>{element['text']}</{element['tag']}>"
            )

        return formatted_elements

    async def _get_element_by_id(self, index: int) -> Optional[Any]:
        """根据传递的索引/id获取对应的元素"""
        # 1.判断当前页面是否存在可交互元素缓存
        if (
            not hasattr(self, "interactive_elements_cache") or 
            not self.interactive_elements_cache or 
            index >= len(self.interactive_elements_cache)
        ):
            return None

        # 2.构建选择器
        selector = f'[data-manus-id="manus-element-{index}"]'
        return await self.page.query_selector(selector)

    async def click(
        self,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """根据传递的索引位置 + xy 坐标实现点击元素"""
        # 1.确保页面存在
        await self._ensure_page()

        # 2.判断传递的是 xy 坐标还是索引位置
        if coordinate_x is not None and coordinate_y is not None:
            await self.page.mouse.click(coordinate_x, coordinate_y)
        elif index is not None:
            try:
                # 根据 index 获取
                element = await self._get_element_by_id(index)
                if not element:
                    return ToolResult(success=False, message="Element not found, index: " + str(index))
    
                # 检查元素是否可见
                is_visible = await self.page.evaluate("""(element) => {
                    if(!element) return false;
                    const rect = element.getBoundingClientRect();
                    const style = getComputedStyle(element);
                    return !(
                        rect.width === 0 || rect.height === 0 ||
                        style.display === 'none' || style.visibility === 'hidden' ||
                        style.opacity === '0'
                    );
                }""", element)
    
                # 如果元素不可见，则执行以下代码
                if not is_visible:
                    # 尝试将页面滚动到该元素的位置
                    await self.page.evaluate("""(element) => {
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }""", element)
                    await asyncio.sleep(1)
    
                # 点击元素
                await element.click(timeout=5000)
                return ToolResult(success=True)
            except Exception as e:
                return ToolResult(success=False, message=f"Failed to click element by index {index}: {str(e)}")
        return ToolResult(success=True)

    async def input(
        self,
        text: str,
        press_enter: bool,
        index: Optional[int] = None,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """根据传递的文本 + 换行标识 + 索引 + xy位置实现输入框文本输入"""

        # 1.确保页面存在
        await self._ensure_page()

        # 2.根据索引或坐标定位元素
        if coordinate_x is not None and coordinate_y is not None:
            # 3.点击指定位置后输入文本
            await self.page.mouse.click(coordinate_x, coordinate_y)
            await self.page.keyboard.type(text)
        elif index is not None:
            try:
                # 根据所用查找元素
                element = self._get_element_by_id(index)
                if not element:
                    return ToolResult(success=False, message="Failed to input text, element not found")

                try:
                    # 先清空原始输入框的内容然后再填充
                    await element.fill("")
                    await element.type(text)
                except Exception as e:
                    return ToolResult(success=False, message=f"Failed to input text, {str(e)}")
            except Exception as e:
                return ToolResult(success=False, message=f"Failed to input text, {str(e)}")

        # 判断是否按 Enter 键
        if press_enter:
            await self.page.keyboard.press("enter")

        return ToolResult(success=True)

    async def move_mouse(
        self,
        coordinate_x: Optional[float] = None,
        coordinate_y: Optional[float] = None,
    ) -> ToolResult:
        """传递 xy 坐标，移动鼠标到指定位置"""
        await self._ensure_page()
        await self.page.mouse.move(coordinate_x, coordinate_y)
        return ToolResult(success=True)

    async def press_key(self, key: str) -> ToolResult:
        """传递按键进行模拟按键操作"""
        await self._ensure_page()
        await self.page.keyboard.press(key)
        return ToolResult(success=True)

    async def select_option(self, index: int, option: int) -> ToolResult:
        """传递索引 + 下拉菜单选项序号，在下拉菜单中选择指定的选项"""
        await self._ensure_page()

        try:
            # 获取元素信息
            element = await self._get_element_by_id(index)
            if not element:
                return ToolResult(success=False, message="Element not found, index: " + str(index))

            # 调用函数直接选择对应选项
            await element.select_option(index=option)
            return ToolResult(success=True)
            
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to select option: {str(e)}")

    
