"""
nano-manus 工具设计思路：
1. 所有工具都必须继承一个 BaseTool 基类，拥有统一的 invoke 方法用于调用该类下对应的工具。
2. 定义一个装饰器，被装饰器修饰的方法会填充 _tool_name、_tool_description、_tool_schema 属性。
3. 工具类可以通过 get_tools 快速获取基于缓存的 schema 参数信息，这样 LLM 就可以便捷调用。
4. LLM 生成的内容有可能会有幻觉，在调用工具前需要筛选出 LLM 生成参数中符合工具的相关数据
"""
 
import inspect
from builtins import ValueError
from typing import Any, Callable, Dict, List

from app.domain.models.tool_result import ToolResult


def tool(
    name: str,
    description: str,
    parameters: Dict[str, Dict[str, Any]],
    required: List[str],
) -> Callable:
    """定义 Anthropic 工具装饰器，用于将一个 函数/方法 添加上对应的工具声明"""

    def decorator(func):
        """装饰器函数，用于将 name/description/parameters/required 转换成对应的属性"""
        # 1.创建工具声明数据结构
        tool_schema = {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        }

        # 2.将对应的属性绑定到 func 上
        func._tool_name = name
        func._tool_description = description
        func._tool_schema = tool_schema

        return func

    return decorator


class BaseToolSet:
    """基础工具类，用于定义一个工具类，管理统一的工具集"""

    name: str = ""  # 工具集的名字

    def __init__(self) -> None:
        """构造函数，完成缓存初始化"""
        self._tools_schema_cache: List[Dict[str, Any]] | None = None
        self._tool_methods_cache: Dict[str, Callable] | None = None

    @classmethod
    def _filter_parameters(
        cls, method: Callable, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """传递method+kwargs并过滤参数，使其符合method参数的要求"""
        filtered_kwrags = {}
        sign = inspect.signature(method)

        # 1.循环遍历 kwargs 的所有数据
        for key, value in kwargs.items():
            if key in sign.parameters:
                filtered_kwrags[key] = value

        return filtered_kwrags

    def _scan_and_validate_tools(self) -> None:
        """扫描所有工具 + 自动重名检测 + 构建缓存"""

        # 1.定义工具列表用于存储对应的数据
        tools_schema = []
        tool_methods = {}

        # 2.循环遍历
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_name"):
                tool_name = getattr(method, "_tool_name")
                if tool_name in tool_methods:
                    raise ValueError(f"检测到重复工具名[{tool_name}],请确保工具名唯一")

                tools_schema.append(getattr(method, "_tool_schema"))
                tool_methods[tool_name] = method

        # 3.保存缓存后并返回
        self._tools_schema_cache = tools_schema
        self._tool_methods_cache = tool_methods

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有已注册的工具列表的 Schema 信息"""
        if self._tools_schema_cache is None:
            self._scan_and_validate_tools()
        return self._tools_schema_cache

    def has_tool(self, tool_name: str) -> bool:
        """传递工具名字，判断工具集下是否存在该工具"""
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if (
                hasattr(method, "_tool_name")
                and getattr(method, "_tool_name") == tool_name
            ):
                return True
        return False

    async def invoke(self, tool_name: str, **kwargs) -> ToolResult:
        """根据传递的工具名+kwargs调用指定工具并获取结果"""
        # 1.执行前确保已经扫描完毕
        if self._tool_methods_cache is None:
            self._scan_and_validate_tools()

        # 2.从字典直接取
        if tool_name not in self._tool_methods_cache:
            raise ValueError(f"工具[{tool_name}] 未找到")

        method = self._tool_methods_cache[tool_name]
        # 3.筛选传递的 kwargs 参数保留 method 对应的参数。
        filtered_kwarfs = self._filter_parameters(method, **kwargs)
        # 4.调用方法获取工具结果
        return await method(**filtered_kwarfs)
