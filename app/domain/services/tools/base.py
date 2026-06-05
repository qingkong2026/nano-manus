"""
nano-manus 工具设计思路：
1. 所有工具都必须继承一个 BaseTool 基类，拥有统一的 invoke 方法用于调用该类下对应的工具。
2. 定义一个装饰器，被装饰器修饰的方法会填充 _tool_name、_tool_description、_tool_schema 属性。
3. 工具类可以通过 get_tools 快速获取基于缓存的 schema 参数信息，这样 LLM 就可以便捷调用。
4. LLM 生成的内容有可能会有幻觉，在调用工具前需要筛选出 LLM 生成参数中符合工具的相关数据
"""
import inspect 
from typing import Dict, List, Any , Callable
from builtins import ValueError

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
                "required": required
            }
        }

        # 2.将对应的属性绑定到 func 上
        func._tool_name = name
        func._tool_description = description
        func._tool_schema = tool_schema

        return func

    return decorator


class BaseTool:
    """基础工具类，用于定义一个工具类，管理统一的工具集"""
    name: str = "" # 工具集的名字

    def __init__(self) -> None:
        """构造函数，完成缓存初始化"""
        self._tools_cache = None

    @classmethod
    def _filter_parameters(cls, method: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """传递method+kwargs并过滤参数，使其符合method参数的要求"""
        filtered_kwrags = {}
        sign = inspect.signature(method)

        # 1.循环遍历 kwargs 的所有数据
        for key, value in kwargs.items():
            if key in sign.parameters:
                filtered_kwrags[key] = value

        return filtered_kwrags

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有已注册的工具列表的 Schema 信息"""
        # 1.判断缓存是否存在
        if self._tools_cache is not None:
            return self._tools_cache

        # 2.定义工具列表用于存储对应的数据
        tools = []

        # 3.循环遍历
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_name"):
                tools.append(getattr(method, "_tool_schema"))

        # 4.保存缓存后并返回
        self._tools_cache = tools
        return tools
                

    def has_tool(self, tool_name: str) -> bool:
        """传递工具名字，判断工具集下是否存在该工具"""
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_name") and getattr(method, "_tool_name") == tool_name:
                return True
        return False
    
    async def invoke(self, tool_name: str, **kwargs) -> ToolResult:
        """根据传递的工具名+kwargs调用指定工具并获取结果"""
        # 1.循环遍历工具集的所有方法
        for _, method in inspect.getmembers(self, inspect.ismethod):
            # 2.判断对应的方法是否存在 _tool_name
            if hasattr(method, "_tool_name") and getattr(method, "_tool_name") == tool_name:
                # 3.筛选传递的 kwargs 参数保留 method 对应的参数。
                filtered_kwarfs = self._filter_parameters(method,**kwargs)

                # 4.调用方法获取工具结果
                return await method(**filtered_kwarfs)

        # 5.如果循环结束还没找到工具并调用则抛出错误
        raise ValueError(f"工具[{tool_name}] 未找到")

        
