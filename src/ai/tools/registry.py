import inspect
from typing import Callable, Dict, Any, List

TOOLS_REGISTRY: Dict[str, Callable] = {}
TOOLS_SCHEMAS: List[Dict[str, Any]] = []

def register_tool(func):
    """装饰器：注册工具并自动生成 OpenAI 格式的 Schema"""
    TOOLS_REGISTRY[func.__name__] = func

    # 简单的 Schema 生成逻辑 (生产环境建议用 Pydantic 生成)
    sig = inspect.signature(func)
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    for name, param in sig.parameters.items():
        param_type = "string" # 简化处理，默认 string
        if param.annotation == int: param_type = "integer"

        parameters["properties"][name] = {
            "type": param_type,
            "description": f"Parameter {name}"
        }
        if param.default == inspect.Parameter.empty:
            parameters["required"].append(name)

    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": parameters
        }
    }
    TOOLS_SCHEMAS.append(schema)
    return func