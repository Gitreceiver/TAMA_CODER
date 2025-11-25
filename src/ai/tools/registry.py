import inspect
from typing import Callable, Dict, Any, List, get_origin, get_args

_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _schema_type_from_annotation(annotation: Any) -> Dict[str, Any]:
    """Convert a Python type annotation to a JSON schema fragment."""
    if annotation in _TYPE_MAP:
        return {"type": _TYPE_MAP[annotation]}

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] -> Union[T, NoneType]
    if origin is list and args:
        item_type = _TYPE_MAP.get(args[0], "string")
        return {"type": "array", "items": {"type": item_type}}
    if origin is dict and len(args) == 2:
        # simplified object map
        return {"type": "object", "additionalProperties": True}

    # Fallback
    return {"type": "string"}

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
        schema_entry = _schema_type_from_annotation(param.annotation)
        schema_entry["description"] = f"Parameter {name}"
        parameters["properties"][name] = schema_entry
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
