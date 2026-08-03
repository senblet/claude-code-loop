# claude-code-loop

An Architect → Builders → Reviewer loop for Claude Code, plus a Designer on work
that has a user interface. Subagents, a review gate, and a memory that learns
from its own mistakes.

```
request or issue
      │
      ▼
  Architect ──── plans and splits the work, writes no code
      │
      ├──▶ Designer ──── UI work only: specs the surface before it is built
      │         │
      ▼         │
  Builders  ◀───┘  one task each, own context, code + tests
      │
      ▼
   one PR
      │
      ▼
  Reviewer  ──── sees only the diff, approves or sends it back
      ▲                                   │
      └── Designer, on its own spec       └──▶ back to the Builders
      │                                        (max 3 rounds)
      ▼
   approved
```

## Why this instead of just asking Claude to do it

The default loop — describe a task, Claude writes it, runs the tests, declares it
done — has one structural problem: **the thing that wrote the code also decides
whether the code is good.** Self-review is generous. It approves its own design
choices because it can still see the reasoning that produced them.

This template splits that into three agents with separate context windows, and a
fourth — a Designer — on work that has a user interface. The Reviewer cannot see
the Builder's reasoning, only the diff: the same position a human reviewer is in,
which is the whole reason human review works.

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

## What actually costs rounds

The three constraints above are all about the review gate. Running this on real
work, the expensive failures turned out to happen earlier — at the plan gate,
where the loop has no way to review itself out of them:

- **An assumption nobody tested.** A plan built on a guess about how an external
  service reports a rejected key. Twenty minutes proving the real behaviour first
  would have collapsed three review rounds into one design decision. The
  Architect now lists what the plan is betting on, and load-bearing guesses
  become a spike task before anyone writes real code.
- **A task that could not be satisfied.** A four-condition checklist with no
  implementation that meets all four. The Builder correctly refused and reported
  `blocked` — a round lost to the instruction, not to the work. Builders now
  check satisfiability before building instead of discovering it after.
- **A measurement that silently measured nothing.** A test glob that matched no
  files, which quietly made two different checks the same check and misdirected a
  round. A test that cannot fail reports success. Builder and Reviewer now both
  confirm new tests actually ran and actually fail without the change.
- **More parallelism than the change was worth.** Four builders on a two-file
  change; the file boundaries and "don't touch that" contracts cost more than the
  parallelism returned. Splitting is now tied to file count rather than to how
  many pieces you can name.

Three of those four were decided before a Builder wrote a line, which is why
extra rounds could never have recovered them. If the loop feels slow, look at the
plan before you look at the agents.

## The Designer, and why it only runs sometimes

Every other kind of disagreement in this loop has something that ends it. A
failing test settles an argument about logic. Nothing settles an argument about
layout — a reviewer can always find something to dislike about an interface, and
the builder can always disagree. So UI work is the worst case for the three-round
cap unless something decides the design *before* the code exists.

That is the Designer's job. On a UI task it runs first, reads the patterns the
repo already has, and writes a spec whose lines become acceptance criteria:
states, interaction, focus order, accessibility, and the exact copy. Then at
review time it is resumed to check the built result against **its own spec** —
running the app, screenshotting each state, and citing a spec line for every
finding.

Two constraints make that safe, and they are the same idea as the Reviewer's edit
budget:

- **It cannot introduce a standard at review time.** A design it now wishes it
  had specified differently is a FOLLOW-UP, not a finding. Builders cannot
  satisfy a spec that did not exist when they built.
- **It does not own the verdict.** Its findings go into the Reviewer's single
  verdict. One gate, not two.

**It should not run on most UI work.** The trigger is a new user-facing surface,
or a change to an existing flow's states or interaction model. Not styling, not
copy edits, not adding a field to a pattern the repo already has — in a project
with established components most interface work is pattern-following, and a
design pass there costs a round and returns nothing.

One honest limit: a screenshot review is only as real as the screenshot. A shot
of a login redirect or an error boundary looks exactly like evidence, so the
Designer has to confirm it captured the surface it specified, and report
`UNVERIFIED` rather than review a page it never loaded.

## What learning actually means here

All four agents use `memory: project`, which gives them a persistent directory
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
python3 path/to/claude-code-loop/install.py your-project
```

Standard library only. It creates the directories, copies the five files, and
checks whether your `.gitignore` swallows `.claude/` or `.claude/agent-memory/`
— the two ways this setup breaks without saying anything.

It never overwrites a file you have edited: a destination that differs from the
template is reported and left alone, and the run exits non-zero. Pass `--force`
to take the template's version anyway. Also `--dry-run` to see the plan, and
`--commit` to stage and commit `.claude/` for you.

Re-running it is safe — that is how you pull template updates into a project
that already has the loop installed.

The equivalent by hand, if you would rather see it:

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
four agents in the picker.

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
| Designer | `opus` | Judgment, and only runs on UI work — so it is rarely the cost. |
| Builders | `sonnet` | Volume work, and the Reviewer catches what it misses. |
| Reviewer | `opus` | Judgment. This is the gate; don't make it dumber than the Builders. |

The three core agents plus a review round run roughly 5–8× a single-session fix;
a task that pulls in the Designer adds a spec pass and a screenshot pass on top.
Sonnet Builders are the main dial and usually the whole saving — but if rounds 2 and 3
fire constantly on the same kind of task, move the Builders back to Opus for that
work rather than loosening the Reviewer.

Note that `CLAUDE_CODE_SUBAGENT_MODEL`, if you have it set, overrides the
frontmatter on *every* subagent — including the Opus pins above.

## Files

```
agents/architect.md   plans and splits; no Edit tool, so it structurally cannot code
agents/builder.md     implements one task, writes tests, applies review findings
agents/designer.md    UI only: specs a surface before it is built, then checks it
agents/reviewer.md    QA gate; verdict format, severity levels, edit budget
commands/ship.md      the orchestrator: routes work, counts rounds, enforces stops
install.py            copies the five files into a project; checks .gitignore
docs/TUNING.md        parallel worktrees, hooks, graduating to a dynamic workflow
```

Everything here is a prompt. Read the agent files and change them — they encode
opinions about code review that are mine, not laws. The three constraints above
are the parts worth keeping.

## License

MIT
