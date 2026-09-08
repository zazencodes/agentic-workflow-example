# agentic-workflow-example

A complete, minimal **agentic workflow**: a markdown spec a coding agent reads,
deterministic scripts it calls, durable state, and exactly one approval gate.

The example workflow is a **repo digest**. You point it at one of your own
projects and it reads the commits and closed issues since a starting point you
choose (a date, a tag, a release, or wherever the last digest stopped), writes a
changelog entry in that project's voice, shows it to you once, and opens a pull
request against it. There is no schedule and nothing to install.

**This repo is the tool, not the subject.** Clone it once, then run it against
whatever you are actually working on. The branch, the `CHANGELOG.md` entry, the
commit and the PR all land in the target project; the only thing written here is
the state file.

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

Requires `git`, `python3`, and an authenticated [`gh`](https://cli.github.com/).
No package installs — the scripts are stdlib only.

```sh
git clone https://github.com/zazencodes/agentic-workflow-example
cd agentic-workflow-example

# Point any CLI agent at the spec, and the spec at one of your projects:
claude "run the repo changelog workflow for ~/code/my-project"
```

Works the same with `codex`, `agy`, or any other CLI coding agent — the spec is
the interface, not the tool.

Leave the path out and it asks:

```sh
claude "run the repo changelog workflow"
# > Which repository should I digest? Give me the path on your machine.
```

You can also just ask for the thing you want, in your own words:

```sh
claude "write up what's changed in ~/code/my-project since the last release"
```

That works because of [`AGENTS.md`](AGENTS.md), which every CLI agent reads
automatically when it starts in this directory. It lists the phrases that mean
"run the repo digest" and tells the agent to open `WORKFLOW.md` and follow it
rather than improvising an answer in chat.

**The two files do different jobs, and it is worth understanding the split:**

- [`AGENTS.md`](AGENTS.md) is the **trigger** — *when* to run the workflow, and
  which plain-English requests should invoke it. Short, and always in context.
- [`WORKFLOW.md`](WORKFLOW.md) is the **program** — *how* to run it. Long, and
  read on demand, only once a run actually starts.

Keeping them apart is what lets you add a tenth workflow to a repo without
putting ten procedures in front of the agent on every unrelated question.

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

The division of labour is the whole trick:

| Give to the agent | Give to a script |
|---|---|
| Grouping commits into themes | Running `git log` over a range |
| Writing the changelog prose | Creating the branch and opening the PR |
| Deciding a run has gone wrong | Recording that the run succeeded |

## Adapt it

The workflow is deliberately small so you can gut it. To point it at your own
repetitive task:

1. Replace `collect_activity.py` with whatever gathers your inputs. Keep the
   `--repo` argument, or whatever names the thing being operated on — an
   automation that assumes the current directory will eventually write to the
   wrong one.
2. Rewrite the Step 2 prose rules for what you actually want written.
   Update the trigger phrases in `AGENTS.md` to match how you'd actually ask.
3. Replace `open_pr.py` with your publish step.
4. Keep the constants block, the single gate, and the state file. Those are the
   parts that make it survive.

Full walkthrough in [`WORKFLOW.md`](WORKFLOW.md).

## More from ZazenCodes

- **Agentic Coding Fundamentals** — the full course: <https://zazencodes.com>
- **Newsletter** — one email a week, plus the guide: <https://zazencodes.com/newsletter>
- **YouTube** — <https://youtube.com/@ZazenCodes>

## License

[MIT](LICENSE). Fork it, gut it, make it yours.
