import os
import shutil
from .registry import register_tool
from src.ai.utils.backup import BackupManager
from config import settings # Import the actual settings

# Instantiate BackupManager with the actual DB_PATH from settings
backup_manager = BackupManager(db_path=settings.DB_PATH)

# We can write a decorator to automatically handle backup
def with_backup(func):
    def wrapper(*args, **kwargs):
        # From the arch.md, assume path is the first argument or in kwargs.get('path')
        path = kwargs.get('path')
        if not path and len(args) > 0 and isinstance(args[0], str):
            path = args[0]

        # From the arch.md, assume task_id is passed as a keyword argument
        task_id = kwargs.get('task_id')

        if task_id and path:
            backup_manager.create_snapshot(task_id, path, func.__name__)

        return func(*args, **kwargs)
    return wrapper

@register_tool
def read_file(path: str, start_line: int = 1, max_lines: int = 400) -> str:
    """
    读取文件内容（可选行范围）。默认最多返回 400 行，防止上下文过大。
    """
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    if start_line < 1:
        return "Error: start_line must be >= 1."
    if max_lines <= 0:
        return "Error: max_lines must be > 0."

    lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if i < start_line:
                    continue
                lines.append(line)
                if len(lines) >= max_lines:
                    lines.append("\n...[truncated]...\n")
                    break
        return "".join(lines)
    except UnicodeDecodeError:
        return f"Error: File {path} is not UTF-8 text."
    except Exception as exc:
        return f"Error reading file {path}: {exc}"

@register_tool
@with_backup
def apply_patch(path: str, original_snippet: str, new_snippet: str, task_id: int) -> str:
    """
    精准替换文件中的代码块。
    original_snippet: 文件中原有的代码片段（必须完全匹配）
    new_snippet: 要替换成的新代码
    task_id: 当前任务的ID，用于备份
    """
    content = read_file(path)
    if "Error" in content: return content

    occurrences = content.count(original_snippet)
    if occurrences == 0:
        return "Error: original_snippet not found in file. Please read file again to ensure context."
    if occurrences > 1:
        return f"Error: original_snippet found {occurrences} times. Please provide a more specific snippet."

    if original_snippet not in content:
        return "Error: original_snippet not found in file. Please read file again to ensure context."

    new_content = content.replace(original_snippet, new_snippet, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return "Success: Patch applied."

@register_tool
def list_files(path: str = ".") -> str:
    """列出目录结构，自动忽略 .git, __pycache__ 等"""
    # 实现类似 tree 命令的输出
    return os.popen(f"git ls-files {path}").read()
