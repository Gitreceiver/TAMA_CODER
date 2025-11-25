import os
import shutil
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime
from config import settings # Import the actual settings

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
