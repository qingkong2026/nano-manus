import logging
import asyncio
from typing import Optional
from playwright.async_api import Playwright, Browser, Page, async_playwright


from app.domain.external.browser import Browser as BrowserProtocol
from app.domain.external.llm import LLM
from app.domain.models.tool_result import ToolResult

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
            is_completed = await self.page.evaluate("""() => document.readyState === 'complete'""")
            if is_completed:
                return True

            # 未加载成功则休眠对面时间
            await asyncio.sleep(check_interval)

        return False

    async def initialize(self) -> bool:
        """初始化并确保资源是可用的"""
        # 1.定义最大重试次数
        max_retries = 3
        retry_interval = 1
        BLANK_PAGE_URLS = {"about:blank", "chrome://newtab", "chrome://new-tab-page/", ""}

        for attempt in range(max_retries):
            try:
                # 1.创建 playwright 上下文并连接到 cdp 浏览器
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)

                # 2.获取浏览器上下文
                contexts = self.browser.contexts

                # 如果上下文存在，并且第一个上下文只有一个页面
                if contexts and contexts[0].pages and  len(contexts[0].pages) == 1:
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
                    logger.error(f"Playwright initialization failed after {max_retries} retries: {str(e)}")
                    return False

                # 使用指数级进行休眠
                retry_interval = max(retry_interval * 2, 10)
                logger.warning(f"Failed to initialize Playwright browser. Retrying attempt {attempt + 1}...")
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
            
    