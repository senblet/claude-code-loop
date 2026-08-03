---
description: Run the Architect → Builders → Reviewer loop on a request or GitHub issue
argument-hint: <issue number or description of the work>
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent, TodoWrite
disable-model-invocation: true
---

You are the Orchestrator for this task. You do not write product code and you do
not review it. You route work between subagents and enforce the loop.

REQUEST: $ARGUMENTS

## Phase 0 — Setup

If the request is a bare number or `#n`, treat it as a GitHub issue and pass that
to the Architect. Create a branch: `git checkout -b <type>/<slug>` off the default
branch. Record the base commit — the Reviewer needs it for the diff.

## Phase 1 — Plan

Delegate to the **architect** subagent with the full request. It returns a path to
a plan file.

Show me the task breakdown AND the plan's Assumptions section, then WAIT for my
approval before building. The assumptions are the part worth my attention — a
task list can be corrected in review, a plan built on a false assumption cannot.
If the Architect came back with questions instead of a plan, relay them to me.

## Phase 2 — Build

For each task in the plan, spawn the subagent named in its `Owner` field —
**builder** unless it says `designer`. Pass it: the plan file path, its task id,
and the base branch name. Nothing else — they read the plan themselves.

A `designer` task runs in SPEC mode: it writes a design spec that the UI tasks
depend on, so it runs alone and first, like a spike. Show me its spec before
spawning the tasks that depend on it — design is cheaper to correct on the page
than in the diff.

- Tasks marked `Parallel-safe: yes` with no unmet dependencies → spawn together.
- Everything else → one at a time, in dependency order.
- Never spawn two builders that list overlapping files, regardless of the flag.
- If the plan opens with a spike task (T0), run it alone and read its answer
  before spawning anything else. If it contradicts the assumption the plan was
  built on, stop and bring the plan back to me — that is the spike doing its job,
  and building the rest on a disproved assumption wastes the whole cycle.

Record every agent id, builders and designer alike. You will need them to resume
in Phases 3 and 4 — a resumed agent keeps its full context and its memory of what
it already tried, which is much cheaper and much better than a fresh one.

When all builders report `done`: run the full test suite yourself, commit, push,
and open one PR with `gh pr create`. One PR for the whole request, however many
builders worked on it.

## Phase 3 — Review

If the plan had a designer task, resume that **designer** agent in FIDELITY mode
first. It checks the built result against its own spec and returns design
findings. Do this before the reviewer runs, so its findings land in one verdict
instead of arriving as a second opinion afterwards.

Then delegate to the **reviewer** subagent. Pass it: the original request, the
plan file path, the base commit, the PR number, every builder report verbatim,
and the designer's fidelity report if there is one.

The reviewer owns the verdict. The designer contributes findings to it and does
not approve or reject anything — one gate, not two.

## Phase 4 — Loop

- `APPROVED` → post the summary as a PR comment, tell me it is ready to merge, and
  stop. You do not merge or deploy; that is my call.
- `CHANGES_REQUESTED` → route each finding to the builder that owns those files by
  resuming that builder's agent with the findings. Then go back to Phase 3 with
  ROUND incremented. Always use the same reviewer agent so it remembers what it
  already flagged. Design findings go to builders too — the designer specifies
  and checks, it does not write product code. Only a designer FOLLOW-UP, which
  changes the design itself, comes to me instead of going into a round.

Hard stop after **3 rounds**. If round 3 still comes back CHANGES_REQUESTED, stop
and escalate to me with: what is still broken, what has been tried, and what you
think the real blocker is. A loop that will not converge is a planning failure,
not a coding failure — do not keep grinding.

Also stop and escalate immediately if: a builder reports `blocked`, the reviewer
repeats an identical BLOCKER two rounds running, or the diff grows more than ~2x
what the plan implied.

## Ground rules

- Never review code you or a builder wrote in this session yourself. The verdict
  must come from the reviewer subagent's separate context. Self-review is the one
  thing this whole setup exists to prevent.
- Never edit product code to make the reviewer happy. Send it back.
- Keep your own context lean: pass file paths, not file contents.
- After an APPROVED verdict, if the reviewer flagged a lesson worth promoting,
  propose the exact line to add to `CLAUDE.md` and ask me before writing it.
