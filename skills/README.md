# Skills

Reusable [Claude Code](https://docs.claude.com/en/docs/claude-code) skills for contributors to this repo.

## Available skills

- [`add-best-practice`](./add-best-practice/SKILL.md) — checklist & workflow for adding a new best practice example.

## Install

Run once from the repo root to symlink every skill into `.claude/skills/` so Claude Code discovers them as slash commands:

```bash
./skills/install.sh
```

After install, invoke a skill in Claude Code with its slash command, e.g. `/add-best-practice`.

> `.claude/` is gitignored, so the symlinks live only in your local checkout. Re-run `install.sh` whenever a new skill is added.
