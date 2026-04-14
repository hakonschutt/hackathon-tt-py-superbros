# Superbros Hackathon — TT Competition

All project context, rules, commands, scripts, and workflow docs are in [AGENTS.md](AGENTS.md).

## Default Behavior

When asked to solve a problem or implement a feature:
1. Read AGENTS.md for project conventions and the **Orchestration** section for dispatch strategy
2. Act as orchestrator — break the problem into parts and dispatch solver agents in parallel worktrees
3. Review and merge results, don't just hand back raw output
4. See [docs/orchestration.md](docs/orchestration.md) for full patterns
