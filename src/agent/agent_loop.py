
import json
import asyncio  # Import asyncio for running async operations
import inspect
from typing import Any
from rich.console import Console
from src.ai.client import client  # Import DeepSeek Client
from src.task_manager.data_models import Task
from src.ai.tools.registry import TOOLS_REGISTRY, TOOLS_SCHEMAS
import src.task_manager.core as core  # Import core to get task details
import task_manager.storage_sqlite as storage

console = Console()

class AgentLoop:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.history = []
        self.max_steps = 30
        self.task: Task | None = None # Explicitly type task as Task or None

    def _init_context(self):
        """构建初始 Prompt，注入 Task 上下文"""
        if not self.task:
            # This should ideally not happen if 'run' loads the task first
            system_prompt = f"""你是一个全栈 AI 工程师。你正在执行一个具体的开发任务。

【当前任务】
ID: {self.task_id}
标题: [无法加载任务详情]
描述: [无法加载任务详情]
详情: [无法加载任务详情]

【执行原则】
1. 即使有上下文，修改前也请先使用 `read_file` 确认最新内容。
2. 修改代码优先使用 `apply_patch`，尽量避免全量 `write_file`。
3. 完成代码后，务必运行测试或创建一个简单的测试脚本验证。
4. 确认无误后，调用 `task_complete` 结束。
"""
        else:
            file_contexts = ""
            for file_path in self.task.linked_files:
                try:
                    file_content = TOOLS_REGISTRY["read_file"](path=file_path, start_line=1, max_lines=400)
                    if "Error" in file_content: # Check for error string from read_file
                        file_contexts += f"\n--- File: {file_path} (Error reading file) ---\n{file_content}\n"
                    else:
                        file_contexts += f"\n--- File: {file_path} ---\n{file_content}\n"
                except Exception as e:
                    file_contexts += f"\n--- File: {file_path} (Error reading file) ---\nCould not read file due to an unexpected error: {e}\n"

            system_prompt = f"""你是一个全栈 AI 工程师。你正在执行一个具体的开发任务。

【当前任务】
ID: {self.task.id}
标题: {self.task.title}
描述: {self.task.description or '无'}
详情: {self.task.details or '无'}

【已知上下文文件】
{file_contexts if file_contexts else '无关联文件'}

【执行原则】
1. 即使有上下文，修改前也请先使用 `read_file` 确认最新内容。
2. 修改代码优先使用 `apply_patch`，尽量避免全量 `write_file`。
3. 完成代码后，务必运行测试或创建一个简单的测试脚本验证。
4. 确认无误后，调用 `task_complete` 结束。你必须明确调用 `task_complete` 工具来结束任务。
"""
        self.history.append({"role": "system", "content": system_prompt})

    async def run(self):
        """执行 Agent 的思考-行动-观察循环"""
        # Load task data first
        tasks_data = storage.load_tasks()
        self.task = core.get_task_by_id(tasks_data.tasks, self.task_id)

        if not self.task:
            console.print(f"[bold red]Task '{self.task_id}' not found for AgentLoop.[/bold red]")
            return False

        self._init_context()
        console.print(f"[bold green]🤖 Agent Started for Task #{self.task.id} - {self.task.title}[/bold green]")

        step = 0
        while step < self.max_steps:
            try:
                console.print(f"[dim]Step {step + 1}/{self.max_steps}[/dim]")
                # 1. 调用 LLM
                response = await client.chat.completions.create(
                    model="deepseek-chat", # For now, hardcode model. This will be configurable.
                    messages=self.history,
                    tools=TOOLS_SCHEMAS,
                    stream=False
                )
                msg = response.choices[0].message
                self.history.append(msg)

                # 2. 处理 Tool Calls
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        console.print(f"[cyan]🔨 执行工具: {func_name} with args: {args}[/cyan]")

                        # Special tool: task_complete - should be implemented as a tool
                        if func_name == "task_complete":
                            console.print("[bold green]🎉 AI 宣布任务完成！[/bold green]")
                            return True

                        # Execute local function
                        func = TOOLS_REGISTRY.get(func_name)
                        if func:
                            # Pass task_id to tools that need it for backup
                            call_args = dict(args)
                            if "task_id" in inspect.signature(func).parameters:
                                call_args.setdefault("task_id", int(self.task_id))

                            if inspect.iscoroutinefunction(func):
                                result = await func(**call_args)
                            else:
                                result = func(**call_args)
                        else:
                            result = f"Error: Tool '{func_name}' not found."

                        # 将结果截断（防止日志爆炸），返还给 AI
                        display_result = result[:500] + "..." if len(result) > 500 else result
                        console.print(f"[dim]   -> {display_result}[/dim]")

                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                elif msg.content:
                    # AI 纯对话
                    console.print(f"[blue]🤖 AI:[/blue] {msg.content}")
                else:
                    console.print("[dim]AI did not return any tool call or content.[/dim]")

                step += 1

            except KeyboardInterrupt:
                console.print("[red]用户中断执行[/red]")
                break
            except Exception as e:
                console.print(f"[red]Engine Error: {e}[/red]")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
                break
        console.print("[bold yellow]Agent reached maximum steps without completing the task.[/bold yellow]")
        return False
