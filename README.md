# claude-code-loop

An Architect → Builders → Reviewer loop for Claude Code. Subagents, a review gate,
and a memory that learns from its own mistakes.

```
request or issue
      │
      ▼
  Architect ──── plans and splits the work, writes no code
      │
      ▼
  Builders  ──── one task each, own context, code + tests
      │
      ▼
   one PR
      │
      ▼
  Reviewer  ──── sees only the diff, approves or sends it back
      │                                    │
      ▼                                    └──▶ back to the Builders
   approved                                     (max 3 rounds)
```

## Why this instead of just asking Claude to do it

The default loop — describe a task, Claude writes it, runs the tests, declares it
done — has one structural problem: **the thing that wrote the code also decides
whether the code is good.** Self-review is generous. It approves its own design
choices because it can still see the reasoning that produced them.

This template splits that into three agents with separate context windows. The
Reviewer cannot see the Builder's reasoning, only the diff — the same position a
human reviewer is in, which is the whole reason human review works.

That's the idea. But the idea is easy and the implementation has three specific
ways to fail. **These three constraints are the actual content of this repo:**

### 1. The Reviewer must not be able to rewrite the code

The dominant failure mode. A Reviewer with full edit access quietly fixes
everything it finds, returns APPROVED every time, and you learn nothing — while
nobody reviews the Reviewer's changes.

`reviewer.md` caps it at roughly ten lines and no design decisions: typos,
missing null guards, a wrong constant, an extra test. Anything structural becomes
a finding and goes back. If you loosen one thing in this template, don't loosen
this one.

### 2. Resume Builders, don't respawn them

When findings come back, they go to the *same* builder agent id. It keeps its
full history — what it tried, what it ruled out, why it chose that approach. A
fresh Builder re-derives the same design from scratch and frequently
reintroduces the same bug.

This is the difference between converging in two rounds and oscillating forever.

### 3. Cap the rounds

Three, then stop and escalate to a human. A loop that won't converge is a
*planning* failure, not a coding failure — more rounds won't fix a task that was
specified wrong. Grinding on it just costs money.

## What learning actually means here

All three agents use `memory: project`, which gives them a persistent directory
at `.claude/agent-memory/<name>/` that survives across sessions and gets loaded
into their prompt at startup.

After a review round, the Builder appends any *repeatable* mistake as a one-line
imperative rule — "always parameterize SQL in the reports module", not "I forgot
to parameterize". Next session, that rule is in its context before it writes the
first line. The Reviewer keeps its own file of recurring findings and flags the
ones worth promoting into `CLAUDE.md`.

**Commit `.claude/agent-memory/`.** If it's gitignored, the loop starts from zero
on every machine and the whole learning mechanism is decorative.

## Install

```bash
cd your-project
mkdir -p .claude/agents .claude/commands .claude/plans

cp path/to/claude-code-loop/agents/*.md      .claude/agents/
cp path/to/claude-code-loop/commands/ship.md .claude/commands/

git add .claude && git commit -m "chore: agent loop"
```

**Restart Claude Code.** A running session doesn't detect a newly created
`agents/` directory. After the first restart, edits to the agent files are picked
up within seconds with no restart needed.

To confirm it loaded: type `/` and look for `ship`, or type `@` and look for the
three agents in the picker.

## Use

```
/ship 412
/ship the signup form accepts emails with no domain, it should reject them
```

A bare number is treated as a GitHub issue. The `gh` CLI needs to be installed
and authenticated for issue reading and PR creation (`gh auth status`); without
it, describe the task in words and open the PR yourself.

The run stops after planning and waits for you. Read the task breakdown before
approving — a wrong plan wastes the entire build and review cycle, and this is
the cheapest place to catch it.

For your first run, pick something small that you already know how to solve. You
want to watch the mechanics — does the Architect over-split, does the Reviewer
actually find things — without simultaneously wondering whether the code is right.

## Add a CLAUDE.md

`CLAUDE.md` loads automatically into every custom subagent. Put your conventions
there — language, test framework, layering, error handling, naming. It's the
cheapest way to stop the Reviewer from flagging the same style issues every
round, because the Builders get the rules *before* they write rather than after.

## Models

| Agent | Default | Why |
|---|---|---|
| Architect | `opus` | A wrong plan costs a whole cycle. Cheapest place to spend. |
| Builders | `sonnet` | Volume work, and the Reviewer catches what it misses. |
| Reviewer | `opus` | Judgment. This is the gate; don't make it dumber than the Builders. |

Three agents plus a review round runs roughly 5–8× a single-session fix. Sonnet
Builders are the main dial and usually the whole saving — but if rounds 2 and 3
fire constantly on the same kind of task, move the Builders back to Opus for that
work rather than loosening the Reviewer.

Note that `CLAUDE_CODE_SUBAGENT_MODEL`, if you have it set, overrides the
frontmatter on *every* subagent — including the Opus pins above.

## Files

```
agents/architect.md   plans and splits; no Edit tool, so it structurally cannot code
agents/builder.md     implements one task, writes tests, applies review findings
agents/reviewer.md    QA gate; verdict format, severity levels, edit budget
commands/ship.md      the orchestrator: routes work, counts rounds, enforces stops
docs/TUNING.md        parallel worktrees, hooks, graduating to a dynamic workflow
```

Everything here is a prompt. Read the agent files and change them — they encode
opinions about code review that are mine, not laws. The three constraints above
are the parts worth keeping.

## License

MIT
