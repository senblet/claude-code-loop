# Tuning

Everything here is optional. Get the default sequential loop converging first —
each of these adds a failure mode of its own.

## Parallel Builders

By default the Builders run sequentially on one branch. Simple, no conflicts, and
for most issues the Architect produces a single task anyway.

For genuinely independent tasks, add to `builder.md`:

```yaml
isolation: worktree
```

Each Builder then works in its own git worktree — an isolated checkout branched
from your default branch — so parallel writes can't collide. The costs:

- The orchestrator has to merge those branches into one integration branch before
  opening the PR.
- A bad decomposition turns into merge conflicts instead of a clean failure.
- The repo needs at least one commit; worktrees can't branch from nothing.

The Architect already marks each task `Parallel-safe: yes/no`. `ship.md` refuses
to spawn two Builders with overlapping file lists regardless of that flag, which
is the backstop for an Architect that was too optimistic.

## Deterministic checks belong in hooks

An agent can talk itself out of a rule. A hook can't. Anything a script can
verify should be verified by a script, so the Reviewer spends its attention on
what only a reader can catch.

`.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "./scripts/lint-changed.sh" }
        ]
      }
    ]
  }
}
```

Hooks defined in `settings.json` fire inside subagents too, so this applies to
every Builder edit without touching the agent files.

Note that project-level hooks require accepting the workspace trust prompt for
the folder. User-level agents in `~/.claude/agents/` don't need it.

## Long standards: use a skill, not a longer CLAUDE.md

`CLAUDE.md` loads into every agent, which is right for universal rules and wrong
for a 400-line style guide. Split long standards into a skill and preload it only
where it's needed:

```yaml
# builder.md
skills:
  - code-standards
```

The full skill text is injected at startup rather than discovered mid-task.

## Reviewer memory → CLAUDE.md promotion

The Reviewer flags findings it has now made more than once. Those should graduate
out of the loop: a rule in `CLAUDE.md` is enforced before code is written, while
a rule in the Reviewer's memory is enforced after. `ship.md` proposes the exact
line and asks before writing it — keep that manual. Auto-promoting review
findings into your project standards is how `CLAUDE.md` becomes 2,000 lines of
accumulated nitpicks that nobody reads.

Curate both memory files. They're checklists, not diaries — merge near-duplicates,
delete rules that went obsolete, keep each under ~50 lines. An agent memory that
grows without bound stops being read carefully, by the agent and by you.

## Graduating to a dynamic workflow

Once `/ship` stops changing, the loop can move into a **dynamic workflow** — a
JavaScript script the Claude Code runtime executes, where the loop, the round
counter and the intermediate results live in script variables instead of in a
context window. Only the final result lands in your session.

Ask for it in a session:

```
use a workflow to run the architect → builders → reviewer loop on issue 412,
capped at 3 review rounds
```

Then `/workflows`, select the run, press `s` to save it as a reusable command in
`.claude/workflows/`.

**The trade-off:** a workflow can't pause for input mid-run, so the
approve-the-plan checkpoint disappears. If you want to keep it, run planning as
one command and build+review as the workflow.

Workflows also spawn every agent in `acceptEdits` mode regardless of your session
setting, so add the commands the Builders need to your allowlist first or you'll
get prompted mid-run anyway.

## When not to use the full loop

The loop earns its cost on changes that cross module boundaries or where being
wrong is expensive. It's overkill for:

- Single-file bug fixes where you already know the fix — go straight to a Builder
  and a Reviewer, skip the Architect.
- Anything you'd merge without human review anyway.
- Exploratory work where the requirements move faster than the plan.

Reaching for `/ship` on everything is the fastest way to conclude the whole
approach isn't worth it.
