# boss-agent-cli — Gemini Context

@./AGENTS.md

> See [AGENTS.md](AGENTS.md) for core architecture and developer CLI contracts.

## Gemini-Specific Notes

- Use `run_shell_command` to execute `boss` CLI commands
- `boss login` may trigger a browser popup for QR code scanning — inform the user to complete authentication in the opened browser window
- Parse JSON output from stdout only; ignore stderr (logs/progress)
- All commands return a JSON envelope with `ok` field — check `ok` before processing `data`
- If `ok=false`, read `error.recovery_action` for self-healing instructions
