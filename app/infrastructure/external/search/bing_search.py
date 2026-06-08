import httpx

import time
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup


from app.domain.models.tool_result import ToolResult
from app.domain.models.search import SearchResultItem, SearchResults
from app.domain.external.search import SearchEngine

logger = logging.getLogger(__name__)

class BingSearchEngine(SearchEngine):
    """Bing搜索引擎"""

    def __init__(self) -> None:
        self.base_url = "https://www.bing.com/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.cookies = httpx.Cookies()

    async def invoke(self, query: str, date_range: Optional[str] = None) -> ToolResult[SearchResults]:
        """根据传递的query+-date_range调用bing搜索获取搜索内容"""

        # 1.构建请求参数
        params = {"q": query}

        # 2.判断 date_range 是否存在并提取真实数据
        if date_range and date_range != "all":
            # 3. 获取当前日期距离 1970-01-01 的天数
            days_since_epoch = int(time.time() / (24 * 60 * 60))

            # 4.创建日期检索数据类型映射
            date_mapping = {
                "past_hour": "ex1%3a\"ez1\"",
                "past_day": "ex1%3a\"ez1\"",
                "past_week": "ex1%3a\"ez2\"",
                "past_month": "ex1%3a\"ez3\"",
                "past_year": f"ex1%3a\"ez5_{days_since_epoch - 365}_{days_since_epoch}\"",
            }

            if date_range in date_mapping:
                params["filters"] = date_mapping[date_range]

        try:
            # 使用 httpx 创建一个异步客户端上下文
            async with httpx.AsyncClient(
                headers=self.headers,
                cookies=self.cookies,
                timeout=60,
                follow_redirects=True,
            ) as client:
                # 调用客户端发起请求
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                # 更新 cookie 信息
                self.cookies.update(response.cookies)

                # 使用 bs4 解析 html 内容
                soup = BeautifulSoup(response.text, "html.parser")

                # 定义搜索结果并解析 li.b_alog 对应的dom元素
                search_results = []

                result_items = soup.find_all("li",class_="b_algo")
                for item in result_items:
                    try:
                        # 标题，url链接
                        title, url = "", ""

                        # 解析搜索结果中的 h2 并提取 title + url
                        title_tag = item.find("h2")
                        if title_tag:
                            a_tag = title_tag.find("a")
                            if a_tag:
                                title = a_tag.get_text(strip=True)
                                url = a_tag.get("href", "")

                        # 判断标题是否存在，如果不存在，则提取该 dom 下的 a 标签中的 href + text 作为标题和链接
                        if not title:
                            a_tags = item.find_all("a")
                            for a_tag in a_tags:
                                text = a_tag.get_text(strip=True)
                                if len(text) > 10 and not text.startswith("http"):
                                    title = text
                                    url = a_tag.get("href","")
                                    break

                        # 如果用两种方式还是没有标题
                        if not title:
                            continue

                        # 提取检索条目的摘要信息
                        snippet = ""
                        snippet_items = item.find_all(
                            ["p","div"],
                            class_=re.compile(r"b_lineclamp|b_descript|b_caption"),
                        )
                        if snippet_items:
                            snippet = snippet_items[0].get_text(strip=True)

                        # 如果这个情况还找不到摘要则查询所有的 p 标签，同时获取文本内容，并判断内容长度是否大于 20
                        if not snippet:
                            p_tags = item.find_all("p")
                            for p in p_tags:
                                text = p.get_text(strip=True)
                                if len(text) > 20:
                                    snippet = text
                                    break

                        # 如果还找不到摘要信息，可以提取元素下的所有文本，并使用常见的分割符进行分割，例如：.!。
                        if not snippet:
                            all_text = item.get_text(strip=True)

                            # 将所有文本按常见的句子结尾标识进行拆分
                            sentences = re.split(r"[.!?\n。！]]", all_text)
                            for sentence in sentences:
                                clean_sentence = sentence.strip()
                                if len(clean_sentence) > 20 and clean_sentence != title:
                                    snippet = clean_sentence
                                    break

                        if url and not url.startswith("http"):
                            if url.startswith("//"):
                                url = "https"+ url
                            elif url.startswith("/"):
                                url = "https://www.bing.com"+ url

                        # 添加数据
                        search_results.append(SearchResultItem(
                            url=url,
                            title=title,
                            snippet=snippet
                        ))

                    except Exception as e:
                        logger.warning(f"Bing搜索结果解析失败: {str(e)}")
                        continue

                # 提取整个页面的内容并查找 results 对应的文本
                total_results = 0
                result_stats = soup.find_all(string=re.compile(r"\d+[,\d+]\s*results"))
                if result_stats:
                    for stat in result_stats:
                        match = re.search(r"([\d,]+)\s*results",stat)
                        if match:
                            try:
                                total_results = int(match.group(1).replace(",",""))
                                break
                            except Exception as e:
                                continue

                if total_results == 0:
                    count_elements = soup.find_all(
                        ["span","p","div"],
                        class_=re.compile(r"sb_count|b_focusTextMedium")
                    )
                    for element in count_elements:
                        # 提起 dom 的文本并获取数字
                        text = element.get_text(strip=True)
                        match = re.search(r"[\d,]+]\s*results",text)
                        if match:
                            try:
                                total_results = int(match.group(1).replace(",",""))
                                break
                            except Exception as e:
                                continue

                # 返回 ToolResult
                results = SearchResults(
                    query=query,
                    date_range=date_range,
                    total_results=total_results,
                    results=search_results,
                )
                return ToolResult(success=True, data=results)
        except Exception as e:
            logger.error(f"Bing搜索出错: {str(e)}")
            error_results = SearchResults(
                query=query,
                date_range=date_range,
                total_results=0,
                results=[],
            )
            return ToolResult(
                success=False,
                message=f"Bing搜索出错: {str(e)}",
                data=error_results
            )