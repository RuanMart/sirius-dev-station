# MEMORY.md — Hermes Persistent Memory

## Active Context
- Sirius Dev Station initialized and connected to the Sirius ecosystem.
- 3-agent orchestration engine active:
  - `opencode` (online): implementation, testing, refactoring.
  - `hermes` (online): persistent memory, background tasks, cron scheduling, MCP tool integration.
  - `agy` (online): Antigravity CLI, BMAD planning, architecture spine, deep research.
- Sirius Context: 108 documents in `.context/` indexed and accessible via `@sirius-mcp/mcp`.
- 57 BMAD skills mapped and runnable.

## Core Rules & Invariants
- Precedence contract: `.context/` is normative authority.
- Repositories are strictly independent:
  - `sirius/` (root)
  - `sirius-api/`
  - `sirius-landing/`
  - `sirius-mcp/`
  - `sirius-dev-station/`
- Windows PowerShell: Use `;` as command separator (avoid `&&`).
- UTF-8 encoding is strictly enforced on all text file reads/writes.
