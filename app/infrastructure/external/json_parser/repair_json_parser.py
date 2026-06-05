import logging
from typing import Any, Dict, List, Optional, Union

import json_repair

from app.domain.external.json_parser import JSONParser

logger = logging.getLogger(__name__)


class RepairJSONParser(JSONParser):
    """基于修复逻辑的 JSON 解析器"""

    async def invoke(
        self, text: str, default_value: Optional[Any] = None
    ) -> Union[Dict, List, Any]:
        """传递文本，并使用 json 修复库进行修复"""

        # 1.记录日志并判断 text 是否为空
        logger.info(f"解析 json 文本: {text}")
        if not text or not text.strip():
            if default_value is not None:
                return default_value
            raise ValueError("json文本为空，且无默认值")

        # 2.text 存在，使用 json_repair 库修复并解析
        return json_repair.repair_json(text, ensure_ascii=False)
