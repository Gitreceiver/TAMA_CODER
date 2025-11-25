# Tama Coder Progress

Progress log for ongoing optimizations beyond the current codebase.

## Done
- Set up progress tracking with this `progress.md`.
- Fixed AgentLoop to load tasks via SQLite storage, import inspect, and handle sync/async tool calls reliably.
- Hardened `run_shell` with cwd sandboxing, timeout, multiline/forbidden command blocking, and output truncation.
- Added guardrails to `apply_patch` to avoid ambiguous replacements.
- Switched remaining task loaders (MCP server, expansion/parsing) to SQLite-backed storage.
- Removed JSON storage path settings/usage; CLI messaging now references SQLite, and legacy storage module/tests were pruned.
- Added DB_PATH in settings, limited linked-file context to partial reads, and exposed `tama undo` CLI using BackupManager snapshots.

## In Progress
- None yet.

## Todo / Planned
- Solidify SQLite storage: ensure single load/save/get API is used everywhere (CLI/Agent/tools), drop remaining JSON docs/tests, and validate schema/init paths. (DB path added; still need doc cleanup.)
- Harden tool layer: allowlist + cwd sandbox + timeout/output truncation for `run_shell`; diff-based `apply_patch`; stronger tool schema (typed JSON schema inference); partial reads to avoid huge contexts. (Partial reads & schema typing done; still need diff-based patch/allowlist.)
- Close the backup/rollback loop: snapshot all write-like tools (including shell), add `tama undo/reset`, implement backup GC and git checkpoints.
- Context management: gitignore-aware file listing, large-file/linked-file slicing, include PRD/dep summaries in prompts.
- Agent loop upgrade: plan+execute (R1+V3), configurable budgets/steps/retries, better error classes, interrupt/resume support.
- CLI/REPL: add `tama chat` interactive mode, improve `tama do` post-run flows (auto/dry-run commit, rollback on failure).
- Observability: structured audit log for tool calls (command, cwd, duration, RC), `tama doctor` for env/schema/git checks.
