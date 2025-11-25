import subprocess
from .registry import register_tool
import src.task_manager.core as core
import src.task_manager.data_models as data_models
import src.cli.ui as ui
from src.cli.main import load_task_data, save_task_data # Import from main for task data

@register_tool
def commit_changes(message: str) -> str:
    """Commits current changes to Git with the given message."""
    try:
        # Add all untracked/modified files
        subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
        # Commit changes
        result = subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True, text=True)
        return f"Success: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"Error committing changes: {e.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

@register_tool
def git_diff() -> str:
    """Shows the current Git diff for staged and unstaged changes."""
    try:
        result = subprocess.run(["git", "diff"], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error getting diff: {e.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

@register_tool
def task_complete(task_id: int) -> str:
    """
    AI 调用此工具来标记当前任务为 'done'。这将触发任务状态更新和可选的 Git 提交。
    此工具应在所有代码修改和验证完成后调用。
    """
    tasks_data = load_task_data()
    task = core.get_task_by_id(tasks_data.tasks, str(task_id))

    if not task:
        return f"Error: Task {task_id} not found."

    # Set status to 'done'
    new_status = "done"
    old_status = task.status

    if old_status == new_status:
        return f"Task {task_id} is already done. No update needed."
    else:
        if core.set_task_status(tasks_data.tasks, str(task_id), new_status, propagate=True):
            save_task_data(tasks_data)
            return f"Success: Task {task_id} status updated from '{old_status}' to '{new_status}'."
        else:
            return f"Error: Failed to update status for task {task_id}."

