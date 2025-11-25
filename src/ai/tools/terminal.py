import os
import subprocess
from pathlib import Path
from .registry import register_tool


def _is_safe_cwd(cwd: str) -> tuple[bool, str]:
    """Ensure cwd stays inside the current project root."""
    try:
        root = Path(os.getcwd()).resolve()
        target = Path(cwd).resolve()
        if root in target.parents or root == target:
            return True, str(target)
        return False, str(target)
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"resolve-error:{exc}"


@register_tool
def run_shell(command: str, timeout: int = 30, cwd: str = ".") -> str:
    """执行 Shell 命令 (如 pytest, ls, mkdir)。限制危险命令，限定工作目录，并截断输出。"""
    forbidden = ["rm -rf", "sudo ", "sudo\t", "sudo\n", " su ", ":(){:|:&};:"]
    if any(token in command for token in forbidden):
        return "Error: Command blocked for safety."

    if "\n" in command:
        return "Error: Multiline commands are blocked for safety."

    safe_cwd, resolved_cwd = _is_safe_cwd(cwd)
    if not safe_cwd:
        return f"Error: Unsafe working directory {resolved_cwd}."

    print(f"\n[System] AI wants to run: {command} (cwd={resolved_cwd}, timeout={timeout}s)")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=resolved_cwd,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        max_len = 4000
        if len(stdout) > max_len:
            stdout = stdout[:max_len] + "\n...[truncated stdout]..."
        if len(stderr) > max_len:
            stderr = stderr[:max_len] + "\n...[truncated stderr]..."
        return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nReturn Code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"
