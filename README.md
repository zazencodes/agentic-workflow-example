# Agentic Workflow Example

A complete, minimal **agentic workflow**.

- a markdown spec a coding agent reads
- deterministic scripts it calls
- durable state
- human-in-the-loop approval gate

## The guide


This repo is the companion to **A Developer's Guide to Agentic Workflows**:
a short PDF with everything you need to get started writing agentic workflows.
I'll send you a copy when you [sign up to my newsletter](https://zazencodes.com/newsletter).

<p align="center">
  <a href="https://zazencodes.com/newsletter?utm_source=github&utm_medium=referral&utm_campaign=agentic-workflow-example-guide">
    <img
      src="docs/assets/agentic-workflows-guide-promo.png"
      alt="Agentic Workflows — a developer's guide to creating structured automations for coding agents"
      width="100%"
    >
  </a>
  <br>
  <a href="https://zazencodes.com/newsletter?utm_source=github&utm_medium=referral&utm_campaign=agentic-workflow-example-guide">Get the free PDF</a>
</p>

## Repo digest

The example workflow is a repo digest that you can point at one of your own
projects. It does the following:

1. Reads recent commits and closed issues
2. Writes a changelog entry
3. Asks you for approval
4. Opens a pull request against it

Here's the file structure:

```
├── AGENTS.md                # when to run it — the natural-language trigger
├── WORKFLOW.md              # the spec the agent reads first
├── scripts/
│   ├── collect_activity.py  # deterministic: git log + gh issue list -> JSON
│   └── open_pr.py           # deterministic: branch, commit, gh pr create
├── state/
│   └── workflow-state.json  # run checkpoints + digests already published
└── templates/
    └── digest.md            # the output shape
```

## Run it

Here's how to run it:
```sh
git clone https://github.com/zazencodes/agentic-workflow-example
cd agentic-workflow-example

# Point any CLI agent at the spec, and the spec at one of your projects:
claude "run the repo changelog workflow for ~/code/my-project"
```

It requires `git`, `python3`, and an authenticated [`gh`](https://cli.github.com/).

You can try it out with `codex`, `agy`, or any other CLI coding agent instead of Claude.

## `AGENTS.md` vs `WORKFLOW.md`

- [`AGENTS.md`](AGENTS.md) is loaded into context for every agent session. It defines the **trigger** — *when* to run the workflow, and which plain-English requests should invoke it.
- [`WORKFLOW.md`](WORKFLOW.md) is the **program** itself. It's loaded as needed (through progressive disclosure).


## What makes this a workflow and not a prompt

A prompt is a message. A workflow is a procedure written down once, in a file the
agent reads at the start of every run. The agent supplies judgment; the file
supplies the memory, the order of operations, and the rules about when to stop
and ask.

Four parts, all of them visible in this repo:

| Part | Here | Why |
|---|---|---|
| **The spec** | [`WORKFLOW.md`](WORKFLOW.md) | Self-contained. An agent with no prior context runs it cold. |
| **The trigger** | [`AGENTS.md`](AGENTS.md) | Maps everyday requests onto the spec, so you invoke it by asking, not by naming a file. |
| **Deterministic scripts** | [`scripts/`](scripts) | Anything that must be identical every run is code, not prose. |
| **Durable state** | [`state/workflow-state.json`](state/workflow-state.json) | Records the step reached and the digests already published. Resumes after a failure without double-publishing. |
| **Approval gates** | [Step 3](WORKFLOW.md#step-3--gate-approve-the-digest) | Exactly one, placed after the work and before anything irreversible. |

### A note on the state file

State does two different jobs here, and only one of them is load-bearing at this
size:

- **`repos[<path>].runs`** is the idempotency index — one entry per project you
  point the workflow at, keyed by the commit each digest covered up to. It is
  what stops a re-run from opening a second PR for work you already published.
  Every workflow that touches the outside world needs this.
- **`active_run`** is the in-flight checkpoint — which step finished last, so an
  interrupted run resumes instead of restarting. For a run this short, it is
  honestly overkill; you could delete it and lose nothing. It is here because
  checkpointing is the part that matters once a workflow grows past a couple of
  minutes: a transcode queue, a batch of forty clips, anything that can hit a
  context limit or a timeout halfway through. Learn the shape on something small
  enough to read.

## More from ZazenCodes

- **Agentic Coding Fundamentals** — the full course:
<https://zazencodes.com/courses/agentic-coding-fundamentals>
- **Newsletter** — one email a week: <https://zazencodes.com/newsletter>
- **YouTube** — <https://youtube.com/@ZazenCodes>

<p align="center">
  <a href="https://zazencodes.com/?utm_source=github&utm_medium=referral&utm_campaign=agentic-workflow-example">
    <img
      src="docs/assets/zazencodes-banner.png"
      alt="ZazenCodes — Engineering for the Agentic Era"
      width="100%"
    >
  </a>
  <br>
  Created by <a href="https://zazencodes.com/">ZazenCodes</a>
</p>

## License

[MIT](LICENSE)
