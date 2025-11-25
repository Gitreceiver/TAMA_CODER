这是一个非常宏大且激动人心的构想！你手中的 `tama-cli` 实际上已经具备了 **Claude Code 所缺乏的核心优势——“结构化的任务管理”**。

目前市面上的 AI 编程工具（如 Claude Code, Cursor, Aider）大多是“会话驱动”的，即你给它一个指令，它执行，然后遗忘。而 `tama-cli` 天生具备“项目驱动”的基因（PRD 解析、任务拆解、依赖管理）。

**核心战略：将 `tama-cli` 从一个“记录员”升级为“执行者”。**

要将 `tama-cli` 打造为超越 Claude Code 的工具，我们需要实施以下**五阶段改造方案**：

---

### 阶段一：架构升级——从“命令模式”到“交互模式 (REPL)”

目前的 `tama` 是单次命令执行（如 `tama add ...`）。AI 编程需要连续的上下文对话。

**改造目标**：创建一个交互式终端环境，类似 `claude` 或 `ipython`。

**具体行动**：
1.  **引入 `prompt_toolkit`**：替换或增强 `typer` 的输入功能，支持多行输入、命令历史、语法高亮。
2.  **新建 `src/agent/` 模块**：
    *   创建一个 `AgentLoop` 类，维护对话历史（Chat History）。
    *   实现“思考-行动-观察”循环（ReAct 模式）。
3.  **实现 `tama chat` 命令**：
    *   进入后，用户可以直接用自然语言对话。
    *   AI 不仅可以回答，还可以**调用工具**。

### 阶段二：赋予“双手”——工具系统 (Tool Use)

目前的 `tama` 主要是在操作 SQLite 数据库。要写代码，AI 需要操作文件系统和终端。

**需要实现的 AI 工具 (Tools)**：
在 `src/ai/tools.py` 中实现以下函数，并利用 DeepSeek/OpenAI 的 Function Calling 能力：

1.  **File System Tools**:
    *   `read_file(path)`: 读取文件内容（支持行号，大文件只读部分）。
    *   `write_file(path, content)`: 全量写入（初期）。
    *   `edit_file(path, search_block, replace_block)`: **关键！** 像 Aider 那样基于搜索替换的补丁修改，避免重写整个文件导致 Token 爆炸。
    *   `list_files(path)`: 查看目录结构 (`ls -R` 或 `tree`)。
2.  **Terminal Tool**:
    *   `run_shell(command)`: 执行 shell 命令（运行测试、linter、git）。需要设置安全白名单（禁止 `rm -rf /`）。
3.  **Tama Integration Tools** (这是你的杀手锏):
    *   AI 可以直接调用 `core.get_task_by_id` 读取当前任务详情。
    *   AI 完成代码后，可以自动调用 `core.set_task_status(id, "done")`。

### 阶段三：核心差异化——“任务驱动开发” (TDD with Tasks)

这是 `tama-cli` 超越 Claude Code 的核心点。

**Claude Code 的痛点**：用户说“做一个登录功能”，Claude 开始写，写着写着就忘了还要做“忘记密码”。
**Tama 的方案**：

**工作流设计**：
1.  用户输入：`tama start`。
2.  **自动上下文加载**：`tama` 自动查找 `next_task`（例如 ID 3: "实现 JWT 校验"）。
3.  **构建 Prompt**：
    *   系统提示词：“你是一个 AI 资深工程师。”
    *   **任务上下文**（来自 SQLite）：标题、描述、依赖项、关联文件 (`linked_files`)。
    *   **文件上下文**：自动读取 `linked_files` 中的代码作为背景知识。
4.  **执行循环**：
    *   AI: "我看到当前任务是实现 JWT。我需要先读取 `auth.py`。"
    *   System: (执行读取，返回内容)
    *   AI: "正在修改 `auth.py` 添加 verify 函数..."
    *   System: (应用修改)
    *   AI: "运行测试 `pytest tests/test_auth.py`"
    *   System: (返回测试通过)
    *   AI: "任务完成。" -> **自动触发 git commit 和 tama complete**。

### 阶段四：上下文管理 (Context Awareness)

编程不仅仅是写代码，而是理解代码。

**技术实现**：
1.  **.gitignore 感知**：在 `list_files` 时必须尊重 gitignore。
2.  **Token 优化**：
    *   实现一个 `ContextManager`。
    *   当 AI 读取大文件时，只把相关部分（definitions, imports）放入 Prompt，或者使用 `ctags` 生成代码地图。
3.  **Tree-sitter 集成** (进阶)：
    *   使用 `tree-sitter` 解析代码结构，让 AI 能通过 "查找类 User 的定义" 来获取代码，而不是读取整个文件。

---

### 具体的代码改造路线图

这是为您量身定制的 **`tama-cli` 进化方案：去 MCP 化、原生工具驱动的 AI 编程终端**。

这个方案的核心理念是：**将项目管理（Tasks）与代码生成（Coding）深度绑定**。AI 不再是漫无目的的对话者，而是**领了任务单（Task ID）的打工人**。

---

## 1. 核心架构设计

我们移除 MCP，采用 **Monolithic (单体)** 架构。所有的工具（文件读写、Shell 执行）都直接作为 Python 函数运行在 `tama` 进程内部。

### 架构图

```mermaid
graph TD
    User[开发者] -->|1. tama do 3| CLI[CLI 入口 (cli/main.py)]
    CLI -->|2. 读取任务| DB[(SQLite)]
    CLI -->|3. 启动引擎| Engine[AI 执行引擎 (ai/engine.py)]
    
    subgraph "AI 自治循环 (Loop)"
        Engine -->|4. 构造 Prompt (含任务+文件上下文)| LLM[DeepSeek API]
        LLM -->|5. 返回 Tool Call| Engine
        Engine -->|6. 调度| ToolRegistry[工具注册表 (ai/tools/registry.py)]
        
        ToolRegistry -->|7. 执行| FS[文件系统工具 (read/write/patch)]
        ToolRegistry -->|8. 执行| Shell[终端工具 (run_command)]
        ToolRegistry -->|9. 执行| Git[Git 工具 (commit/diff)]
        
        FS & Shell & Git -->|10. 返回执行结果| Engine
    end
    
    Engine -->|11. 任务完成 & 更新状态| DB
```

---

## 2. 详细改造路线图

### 第一阶段：基础设施 (Tools Layer)

AI 需要“手”来操作电脑。我们需要构建一套 Python 原生工具库。

**文件结构变更**：
```text
src/ai/
├── __init__.py
├── client.py          # 保持原有的 DeepSeek Client
├── engine.py          # [新增] Agent 核心循环
└── tools/             # [新增] 工具包
    ├── __init__.py
    ├── registry.py    # 工具注册与 Schema 生成
    ├── filesystem.py  # 文件读写、Patch
    ├── terminal.py    # Shell 命令执行
    └── git.py         # Git 操作
```

#### 关键代码实现：

**1. `src/ai/tools/registry.py` (工具注册中心)**
```python
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
```

**2. `src/ai/tools/filesystem.py` (文件操作)**
```python
import os
from .registry import register_tool

@register_tool
def read_file(path: str) -> str:
    """读取文件内容。必须提供相对路径。"""
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    with open(path, "r", encoding="utf-8") as f:
        # TODO: 这里未来可以加 Token 限制，大文件只读部分
        return f.read()

@register_tool
def apply_patch(path: str, original_snippet: str, new_snippet: str) -> str:
    """
    精准替换文件中的代码块。
    original_snippet: 文件中原有的代码片段（必须完全匹配）
    new_snippet: 要替换成的新代码
    """
    content = read_file(path)
    if "Error" in content: return content
    
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
    return os.popen(f"git ls-files {path}").read() # 利用 git ls-files 自动处理 gitignore
```

**3. `src/ai/tools/terminal.py` (执行命令)**
```python
import subprocess
from .registry import register_tool
import typer

@register_tool
def run_shell(command: str) -> str:
    """执行 Shell 命令 (如 pytest, ls, mkdir)。禁止交互式命令。"""
    # 安全拦截
    forbidden = ["rm -rf", "sudo", "su"]
    if any(f in command for f in forbidden):
        return "Error: Command blocked for safety."
    
    # Human-in-the-loop: 敏感操作请求确认
    # 在实际运行中，可以通过环境变量控制是否自动确认
    print(f"\n[System] AI wants to run: {command}")
    
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn Code: {result.returncode}"
    except Exception as e:
        return f"Error executing command: {str(e)}"
```

---

### 第二阶段：大脑 (Agent Engine)

这是 `tama-cli` 的核心控制器。

**`src/ai/engine.py`**
```python
import json
from typing import List
from rich.console import Console
from src.ai.client import client  # 复用你现有的 client
from src.task_manager.data_models import Task
from src.ai.tools.registry import TOOLS_REGISTRY, TOOLS_SCHEMAS

console = Console()

class AgentEngine:
    def __init__(self, task: Task):
        self.task = task
        self.history = []
        self.max_steps = 30

    def _init_context(self):
        """构建初始 Prompt，注入 Task 上下文"""
        # 自动读取关联文件内容，减少 AI 探索步骤
        file_contexts = ""
        for file_path in self.task.linked_files:
            try:
                with open(file_path, "r") as f:
                    file_contexts += f"\n--- File: {file_path} ---\n{f.read()}\n"
            except:
                pass

        system_prompt = f"""你是一个全栈 AI 工程师。你正在执行一个具体的开发任务。
        
【当前任务】
ID: {self.task.id}
标题: {self.task.title}
描述: {self.task.description}
详情: {self.task.details}

【已知上下文文件】
{file_contexts}

【执行原则】
1. 即使有上下文，修改前也请先使用 `read_file` 确认最新内容。
2. 修改代码优先使用 `apply_patch`，尽量避免全量 `write_file`。
3. 完成代码后，务必运行测试或创建一个简单的测试脚本验证。
4. 确认无误后，调用 `task_complete` 结束。
"""
        self.history.append({"role": "system", "content": system_prompt})

    def run(self):
        self._init_context()
        console.print(f"[bold green]🤖 Agent Started for Task #{self.task.id}[/bold green]")
        
        step = 0
        while step < self.max_steps:
            try:
                # 1. 调用 LLM
                response = client.chat.completions.create(
                    model="deepseek-chat", # 编码推荐用 V3，规划推荐用 R1
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
                        
                        console.print(f"[cyan]🔨 执行工具: {func_name}[/cyan]")
                        
                        # 特殊工具：任务完成
                        if func_name == "task_complete":
                            console.print("[bold green]🎉 AI 宣布任务完成！[/bold green]")
                            return True

                        # 执行本地函数
                        func = TOOLS_REGISTRY.get(func_name)
                        if func:
                            result = func(**args)
                        else:
                            result = "Error: Tool not found"
                        
                        # 将结果截断（防止日志爆炸），返还给 AI
                        display_result = result[:200] + "..." if len(result) > 200 else result
                        console.print(f"[dim]   -> {display_result}[/dim]")

                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                else:
                    # AI 纯对话
                    console.print(f"[blue]🤖 AI:[/blue] {msg.content}")
                
                step += 1
            
            except KeyboardInterrupt:
                console.print("[red]用户中断执行[/red]")
                break
            except Exception as e:
                console.print(f"[red]Engine Error: {e}[/red]")
                break
```

---

### 第三阶段：交互入口 (CLI Integration)

**修改 `src/cli/main.py`**

```python
from src.ai.engine import AgentEngine
import src.ai.tools.filesystem # 必须导入以触发注册
import src.ai.tools.terminal   # 必须导入以触发注册

@app.command(name="do")
def do_task(
    task_id: str = typer.Argument(..., help="Task ID to execute"),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation prompts")
):
    """🔥 核心功能：AI 自动执行指定任务"""
    tasks_data = load_task_data()
    task = core.get_task_by_id(tasks_data.tasks, task_id)
    
    if not task:
        ui.console.print(f"[red]Task {task_id} not found[/red]")
        return

    # 1. 自动创建分支 (Git Integration)
    branch_name = f"feature/task-{task.id}"
    git_utils.create_branch(branch_name)

    # 2. 启动引擎
    engine = AgentEngine(task)
    success = engine.run()

    # 3. 善后处理
    if success:
        if typer.confirm("任务已完成，是否提交代码并更新任务状态？"):
            git_utils.commit_changes(f"feat: Complete task #{task.id} {task.title}")
            core.set_task_status(tasks_data.tasks, task_id, "done")
            save_task_data(tasks_data)
            ui.console.print("[green]✅ 流程结束[/green]")
```

---

### 第四阶段：上下文增强 (Advanced)

为了超越 Claude Code，你需要实现它做不到的事情：**基于项目结构的记忆**。

1.  **任务依赖链感知**：
    在 `_init_context` 中，不仅读取当前任务，还要读取 **它的前置依赖任务（Dependencies）** 的完成情况和相关文件。
    *   *Prompt 增加*: "注意：此任务依赖于 Task #1 (已完成)，请确保兼容 Task #1 的接口。"

2.  **PRD 持续对齐**：
    在 `TasksData` 中存储原始 PRD 的摘要。每次执行任务时，在 System Prompt 顶部加入：“项目核心目标：[PRD摘要]”，防止 AI 在细节中跑偏。

3.  **R1 思考模式 (DeepSeek Reasoner)**：
    在 `AgentEngine` 中增加一个 `plan` 阶段。
    *   第一步：调用 `deepseek-reasoner` (R1)，不给工具，只给任务，让它输出一段 `Thinking Process` 和 `Implementation Plan`。
    *   第二步：将 R1 的 Plan 作为上下文，传给 `deepseek-chat` (V3)，让 V3 负责调用工具写代码。
    *   **优势**：R1 的逻辑推理能力极强，能避免“写了改，改了写”的死循环。

---

### 总结：核心竞争力

1.  **Structure-First**: 先有任务结构，再写代码。Claude Code 是 Chat-First。
2.  **Local Control**: 没有中间商赚差价，所有工具逻辑你都可以修改（比如你可以自己写一个工具叫 `deploy_to_my_server`，这是 Claude Code 做不到的）。
3.  **Cost Effective**: 配合 DeepSeek V3/R1，成本是 Claude 3.5 Sonnet 的几十分之一，适合大规模自动化。


# 回溯功能

这是一个非常关键的功能。**“可逆性” (Reversibility)** 是开发者敢于放心使用 AI 工具的前提。如果 AI 把代码改乱了却无法一键复原，用户就会因为恐惧而放弃使用。

为了实现**完整且可靠**的代码回溯，采用 **“双层保险机制”**：
1.  **微观层（原子级）**：基于文件快照的 Undo/Redo 栈。
2.  **宏观层（任务级）**：基于 Git 的自动还原点 (Checkpoint)。

以下是具体的实现方案：

---

### 方案核心：构建 `SnapshotManager` (快照管理器)

我们需要在 SQLite 中记录每一次文件操作的“前世今生”。

#### 1. 数据库设计升级

在 `src/task_manager/storage_sqlite.py` 的 `initialize_database` 中增加两张表：

```sql
-- 操作日志表：记录 AI 的每一步物理操作
CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    tool_name TEXT,       -- 例如 "write_file", "apply_patch", "run_shell"
    target_path TEXT,     -- 受影响的文件路径
    backup_path TEXT,     -- 变更前的文件备份路径 (在 .tama/backups/ 下)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 任务会话表：记录 Git 状态
CREATE TABLE IF NOT EXISTS task_sessions (
    task_id INTEGER PRIMARY KEY,
    start_commit_hash TEXT, -- 任务开始时的 Git Commit Hash
    is_dirty_start BOOLEAN  -- 开始时是否有未提交的更改
);
```

---

### 第一层保险：原子级回滚 (Atomic Undo)

这允许用户执行 `tama undo` 来撤销 AI 的上一步操作（例如撤销一次错误的 `apply_patch`）。

#### 实现步骤：

**1. 新建 `src/ai/utils/backup.py`**

```python
import os
import shutil
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime
from config import settings

BACKUP_DIR = Path(settings.TASKS_DIR_PATH).parent / ".tama" / "backups"

class BackupManager:
    def __init__(self, db_path=None):
        self.db_path = db_path
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, task_id: int, file_path: str, tool_name: str) -> int:
        """在修改文件前，保存副本"""
        if not os.path.exists(file_path):
            return None # 新建文件不需要备份内容，但在日志里要记下来以便删除

        # 生成备份文件路径
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = os.path.basename(file_path)
        backup_path = BACKUP_DIR / f"{task_id}_{timestamp}_{unique_id}_{filename}"

        # 物理复制
        shutil.copy2(file_path, backup_path)

        # 写入数据库日志
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO operation_logs (task_id, tool_name, target_path, backup_path) VALUES (?, ?, ?, ?)",
                (task_id, tool_name, str(file_path), str(backup_path))
            )
            return cursor.lastrowid

    def undo_last_operation(self, task_id: int):
        """撤销上一步操作"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 找到最后一条操作记录
            cursor.execute(
                "SELECT id, tool_name, target_path, backup_path FROM operation_logs WHERE task_id = ? ORDER BY id DESC LIMIT 1", 
                (task_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return "No operations to undo."

            op_id, tool_name, target_path, backup_path = row

            try:
                if tool_name in ["write_file", "apply_patch"]:
                    if backup_path and os.path.exists(backup_path):
                        # 恢复文件
                        shutil.copy2(backup_path, target_path)
                        msg = f"Restored {target_path} from backup."
                    elif not backup_path and os.path.exists(target_path):
                        # 如果没有备份路径，说明当时是新建文件 -> Undo 就是删除它
                        os.remove(target_path)
                        msg = f"Deleted created file {target_path}."
                    else:
                        msg = "Backup file missing, cannot undo."
                
                # 删除日志记录
                cursor.execute("DELETE FROM operation_logs WHERE id = ?", (op_id,))
                conn.commit()
                return f"Success: {msg}"
            except Exception as e:
                return f"Undo Failed: {e}"
```

**2. 修改 `src/ai/tools/filesystem.py` 集成备份**

在工具执行前，强制调用备份。

```python
from src.ai.utils.backup import BackupManager

# 假设有一个全局的 backup_manager，或者通过 context 传入
backup_manager = BackupManager(settings.DB_PATH)

# 我们可以写一个装饰器来自动处理备份
def with_backup(func):
    def wrapper(*args, **kwargs):
        # 从参数中提取 path 和 task_id (这就要求工具函数签名要规范)
        # 这里简化处理，假设 path 是第一个参数
        path = kwargs.get('path') or args[0]
        
        # 获取当前上下文的 task_id (这通常在 Engine 运行时设定)
        # 这里假设有一个全局 context 或者通过 kwargs 传入 task_id
        task_id = kwargs.get('task_id') 
        
        if task_id:
            backup_manager.create_snapshot(task_id, path, func.__name__)
            
        return func(*args, **kwargs)
    return wrapper

@register_tool
@with_backup  # <--- 加上这个
def apply_patch(path: str, original: str, new: str, task_id: int = 0) -> str:
    # ... 原有逻辑 ...
```

---

### 第二层保险：任务级回滚 (Git Checkpoint)

这允许用户在任务执行失败后，一键回到任务开始前的状态（`tama reset <task_id>`）。

#### 实现步骤：

**1. 修改 `src/ai/engine.py` 的 `run` 方法**

在任务开始前，创建一个 Git 还原点。

```python
import subprocess

class AgentEngine:
    def _create_checkpoint(self):
        """创建任务开始前的 Git 还原点"""
        # 1. 检查是否有未提交的更改
        status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        is_dirty = bool(status.stdout.strip())
        
        if is_dirty:
            # 自动 Stash，保存现场
            subprocess.run(f"git stash push -m 'tama_checkpoint_task_{self.task.id}'", shell=True)
            # 记录：这是一个脏启动，回滚时需要 pop stash
            self._save_session_state(is_dirty_start=True)
        else:
            # 记录当前 HEAD hash
            head = subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True).stdout.strip()
            self._save_session_state(is_dirty_start=False, commit_hash=head)

    def _restore_checkpoint(self):
        """回滚整个任务"""
        state = self._get_session_state()
        
        # 1. 硬重置当前工作区（丢弃 AI 做的一切修改）
        subprocess.run("git reset --hard", shell=True)
        subprocess.run("git clean -fd", shell=True) # 删除 AI 新建的未追踪文件

        # 2. 如果开始前有 stash，还原它
        if state['is_dirty_start']:
            subprocess.run("git stash pop", shell=True)
        
        print(f"已将代码库回滚到任务 #{self.task.id} 开始前的状态。")
```

---

### 第三步：CLI 命令支持 (`src/cli/main.py`)

暴露给用户使用的命令。

```python
@app.command(name="undo")
def undo_last_step(task_id: str = typer.Argument(..., help="Task ID")):
    """撤销 AI 对该任务的最后一次文件修改"""
    bm = BackupManager()
    result = bm.undo_last_operation(int(task_id))
    ui.console.print(f"[yellow]{result}[/yellow]")

@app.command(name="reset")
def reset_task(task_id: str = typer.Argument(..., help="Task ID")):
    """危险：彻底回滚该任务期间的所有代码变更"""
    if typer.confirm(f"确定要清除任务 #{task_id} 的所有代码更改吗？这将不可恢复。"):
        # 这里调用 Engine 的 restore 方法，或者单独提取出来
        # 实际实现中，建议把 _restore_checkpoint 提取到 git_utils.py
        from src.git_utils import restore_task_checkpoint
        restore_task_checkpoint(task_id)
        ui.console.print("[red]任务已回滚[/red]")
```

---

### 方案亮点总结

1.  **无感备份**：用户不需要手动 commit，每次 AI 修改文件，系统都会在 `.tama/backups` 目录下偷偷存一份副本。
2.  **双向安全**：
    *   AI 改错了一行代码 -> 用 `tama undo` (基于文件副本)。
    *   AI 把整个项目搞挂了 -> 用 `tama reset` (基于 Git Stash/Reset)。
3.  **非侵入式**：不会像某些工具那样产生大量的 "AI WIP" commit 污染用户的 Git 历史。所有的中间状态都由 `tama` 自己管理，只有用户确认满意（`tama complete`）时，才产生真正的 Git Commit。

### 实施建议

在开发 `src/ai/tools/filesystem.py` 时，务必将 **BackupManager** 深度集成进去。这是 `tama-cli` 区别于普通脚本工具的关键——**它不仅会写代码，更懂得保护代码**。