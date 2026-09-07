# agentic-workflow-example

A complete, minimal **agentic workflow**: a markdown spec a coding agent reads,
deterministic scripts it calls, durable state, and exactly one approval gate.

The example workflow is a **weekly repo digest**. It reads the week's commits and
closed issues, writes a changelog entry in your project's voice, shows it to you
once, and opens a pull request with it.

```
├── WORKFLOW.md              # the spec the agent reads first
├── scripts/
│   ├── collect_activity.py  # deterministic: git log + gh issue list -> JSON
│   └── open_pr.py           # deterministic: branch, commit, gh pr create
├── state/
│   └── digest-index.json    # which weeks have been digested
└── templates/
    └── digest.md            # the output shape
```

## Run it

Requires `git`, `python3`, and an authenticated [`gh`](https://cli.github.com/).
No package installs — the scripts are stdlib only.

```sh
git clone https://github.com/zazencodes/agentic-workflow-example
cd agentic-workflow-example

# Point any CLI agent at the spec:
claude "Run the workflow in WORKFLOW.md for last week."
```

Works the same with `codex`, `agy`, or any other CLI coding agent — the spec is
the interface, not the tool.

## The guide

This repo is the companion to **[A Developer's Guide to Agentic Workflows](https://zazencodes.com/newsletter)** —
a short PDF on why you should stop prompting and start specifying, what the four
parts of a workflow are, and the five rules that keep one working six months
later. It's free with the newsletter.

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

## What makes this a workflow and not a prompt

A prompt is a message. A workflow is a procedure written down once, in a file the
agent reads at the start of every run. The agent supplies judgment; the file
supplies the memory, the order of operations, and the rules about when to stop
and ask.

Four parts, all of them visible in this repo:

| Part | Here | Why |
|---|---|---|
| **The spec** | [`WORKFLOW.md`](WORKFLOW.md) | Self-contained. An agent with no prior context runs it cold. |
| **Deterministic scripts** | [`scripts/`](scripts) | Anything that must be identical every run is code, not prose. |
| **Durable state** | [`state/digest-index.json`](state/digest-index.json) | Makes a re-run safe. No double-published PRs. |
| **Approval gates** | [Step 3](WORKFLOW.md#step-3--gate-approve-the-digest) | Exactly one, placed after the work and before anything irreversible. |

The division of labour is the whole trick:

| Give to the agent | Give to a script |
|---|---|
| Grouping commits into themes | Running `git log` over a date range |
| Writing the changelog prose | Creating the branch and opening the PR |
| Deciding a run has gone wrong | Recording that the run succeeded |

## Adapt it

The workflow is deliberately small so you can gut it. To point it at your own
repetitive task:

1. Replace `collect_activity.py` with whatever gathers your inputs.
2. Rewrite the Step 2 prose rules for what you actually want written.
3. Replace `open_pr.py` with your publish step.
4. Keep the constants block, the single gate, and the state index. Those are the
   parts that make it survive.

Full walkthrough in [`WORKFLOW.md`](WORKFLOW.md).

## More from ZazenCodes

- **Agentic Coding Fundamentals** — the full course: <https://zazencodes.com>
- **Newsletter** — one email a week, plus the guide: <https://zazencodes.com/newsletter>
- **YouTube** — <https://youtube.com/@ZazenCodes>

## License

[MIT](LICENSE). Fork it, gut it, make it yours.
