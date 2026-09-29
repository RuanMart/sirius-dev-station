# agy (Antigravity CLI) — Sirius Dev Station Config

The **agy** CLI (Antigravity) acts as the architecture, planning, and deep research agent in the Sirius Dev Station and Sirius Ecosystem.

## Model Configuration
- **Model**: `gemini-3.8-flash-high` (Gemini 3.8 Flash with High Reasoning Effort)
- **Flag**: `--model gemini-3.8-flash-high` (or `--model gemini-3.8-flash --effort high`)
- **Non-interactive execution**: `agy --model gemini-3.8-flash-high --print "<query>"`

## BMAD Alignment
Per Sirius `AGENTS.md` mandate:
- All BMAD personas executing under Antigravity CLI run **Gemini 3.8 Flash with High Effort** (`Model: "inherit"`).
- Personas: Mary (Analyst), John (PM), Sally (UX), Winston (Architect), Amelia (Dev), QA Lead.

## Integration in Sirius Dev Station
- Invoked via `execute_agent("agy", message, repo=repo)` in `server.py` with `--model gemini-3.8-flash-high` and timeout 180s.
- Registered in `data/agent-routes.json` under `agent_capabilities`.
- Status checked via `shutil.which("agy")` in `check_agent()`.
