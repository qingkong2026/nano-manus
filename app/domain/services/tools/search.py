from typing import Optional

from app.domain.models.tool_result import ToolResult

from .base import BaseToolSet, tool
from app.domain.external.search import SearchEngine

class SearchToolSet(BaseToolSet):
    """搜索工具包，提供与搜索引擎交付的能力"""

    name: str = "search"

    def __init__(self, search_engine: SearchEngine) -> None:
        super().__init__()
        self.search_engine = search_engine

    @tool(
        name="search_web",
        description="全网搜索引擎工具。当需要获取实时信息（如突发新闻、天气）、补充内部知识库未涵盖的内容或进行事实核查时使用。该工具会返回相关的网页摘要和链接。",
        parameters={
            "query": {
                "type": "string",
                "description": "针对搜索引擎优化的查询字符串。请提取问题中的核心实体和关键词(3-5个)，避免使用完整的自然语言句子。（例如：将 '今天北京的天气怎么样' 改为'北京 天气'）"
            },
            "date_range": {
                "type": "string",
                "enum": ["all","past_hour", "past_day", "past_week", "past_month", "past_year"],
                "description": "(可选)搜索结果的时间范围过滤。当用户询问特定时效性的新闻或事件时（如 ’昨天‘,'上周'),必须指定此采纳数，默认为 'all' "
            }
        },
        required=["query"]
    )
    async def search_web(self, query: str, date_range: Optional[str] = None) -> ToolResult:
        """调用搜索引擎获取搜索结果后返回"""
        return await self.search_engine.invoke(query=query, date_range=date_range)