---
owner: framework-maintainer
load_when: a team is about to adopt AIDF in a project and needs the exact steps, in order, from nothing
max_length: 6 pages
last_verified: 2026-11-06
---

# How to set up AIDF in a project

This page assumes you know nothing about AIDF and have not started. Do the steps in order, once, before your first governed change. Every command is given for macOS or Linux and for Windows; type or paste it exactly. This page adds no rule of its own: it puts the setup of `README.md` ("Getting started") and the two playbooks in one sequence, and when it and those documents differ, they govern.

**What you will have at the end.** A copy of AIDF on your computer; two named people (a Change Owner and an Architect); a folder of project documents (the *context pack*) that a script has checked; a recorded statement of how your agent may work; and a prompt to start your first change.

## Before you begin: what you need

- **A terminal.** macOS: open *Terminal*. Linux: open your terminal. Windows: open *PowerShell* (Start menu, type `PowerShell`).
- **Git.** Check: type `git --version` and press Enter. If it prints a version, go on. If it says the command is not found, install Git from `https://git-scm.com/downloads`, close the terminal, open a new one, and check again.
- **Python 3.12 or newer** (the AIDF pipeline runs 3.12). Check on macOS or Linux: `python3 --version`. Check on Windows: `python --version`. If it is older than 3.12 or not found, install Python from `https://www.python.org/downloads/`, open a new terminal, and check again. Wherever this page says `python3`, Windows users type `python`.
- **Your project** is a folder on your computer. If it has code already, it is a Git repository with at least one commit. Check: `git log --oneline -1` prints one line. If it prints `fatal: not a git repository`, run `git init` in the project folder first. If it then prints an error or nothing (no commit yet), commit your code: `git add -A`, then `git commit -m "Initial commit"`. If the commit stops with `Author identity unknown`, tell Git who you are once (use your own name and email address), then repeat the commit: `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.
- **The address of the AIDF repository:** `https://github.com/woffordscott-ops/AIDF.git`. It is a public repository: anyone can clone it and you do not need an account. If the clone fails, check that you typed the address exactly as shown and that you are online; if it still fails, ask the person who gave you AIDF.

## Step 1. Get AIDF and check that it runs

1. In the terminal, go to the folder that *contains* your project, not into the project: `cd` to it. Example: if your project is `C:\work\shop` or `/home/me/shop`, go to `C:\work` or `/home/me`.
2. Download AIDF into a new folder named `aidf` next to your project:

   ```
   git clone https://github.com/woffordscott-ops/AIDF.git aidf
   ```

3. Go into it: `cd aidf`
4. Run its checks. macOS or Linux: `python3 -m unittest discover -s verification/tests`. Windows: `python -m unittest discover -s verification/tests`. This takes several minutes and prints a lot.
5. Read the last lines. The line `OK` (possibly `OK (skipped=...)`) means it ran; the number of tests is not important (the AIDF `README.md` may quote an older number). If you see `FAILED` or `Error`, stop and ask the person who gave you AIDF: do not continue on a copy that fails its own checks.
6. Write down the full path of the `aidf` folder (macOS or Linux: type `pwd`; Windows: type `(Get-Location).Path`). The rest of this page calls it `<AIDF>`.

## Step 2. Name the two people

AIDF needs two roles held by someone before anything else (`core/02-authority.md` section 1). One person can hold both.

- **Change Owner**: a human, always. Accountable for what merges; accepts risk; the only party who can waive a control that is not a trip-wire (a trip-wire cannot be waived).
- **Architect**: owns the project's contracts, boundaries and invariants; approves Task Contracts at class T2 and T3.

Create a file in your project named `docs/AIDF-ROLES.md` (create the `docs` folder if you have none; the name is a suggestion, AIDF does not prescribe one) with these lines, filled in:

```
Change Owner: <full name>
Architect: <full name>
```

## Step 3. Read the kernel

Open `<AIDF>/KERNEL.md` in any text editor and read it. It is two pages: ten principles, the rule about what evidence can and cannot decide, the trip-wires (kinds of change that always get the highest class), and the order in which to pick controls. You do not need to memorise it; your agent reads it for every task.

## Step 4. Build the project context pack

The context pack is a folder named `context/` and one file, `project-context-pack.json`, at the root of your project. It describes your project's architecture so that agents and reviewers work from the same facts. The starter in this repository gives you every file with the correct header; you then fill in the content.

1. **Copy the starter into your project root.** First go to your project folder (`cd` to it), then:
   - macOS or Linux: `cp -r <AIDF>/instantiation/starter/. .`
   - Windows PowerShell: `Copy-Item -Recurse -Force <AIDF>\instantiation\starter\* .`

   You now have `project-context-pack.json` and a `context/` folder with ten Markdown files and `pattern-registry.json`.
2. **Name the project.** Open `project-context-pack.json`, and replace `YOUR-ORG/YOUR-PROJECT` with your organisation and project name. Keep the quotation marks. Edit the file in a plain editor that saves UTF-8 without a byte-order mark (Visual Studio Code does). Do not write it with Windows PowerShell 5.1 (`Set-Content -Encoding utf8` adds a byte-order mark), because the checker in part 4 then fails with `FAIL: Unexpected UTF-8 BOM`; saving the file again without the mark fixes it.
3. **If your project already has code (and only then), record its files.** First commit all your code, so that the latest commit is the code you want described. The script at the end of this page ("The script for step 4.3") reads the latest commit and writes that commit and the list of its files into the manifest and `context/repository-map.md`. Copy it into a text editor and save it as `make_pack.py` in a folder *outside* your project (your home folder will do), then, from your project folder, run `python3 <folder>/make_pack.py` (Windows: `python <folder>\make_pack.py`).


   Run it *before* you commit the new `context/` folder, so that the commit it records is your code and the list is your code's files. (If you ran it after committing the pack, the checker still passes, but the list then includes the pack's own files; run it again before the commit to get the clean list.)
4. **Run the checker.** From your project folder: `python3 <AIDF>/instantiation/check_context_pack.py --project-root . --manifest project-context-pack.json` (Windows: `python`, and `<AIDF>\instantiation\check_context_pack.py`). A pass prints: `PASS: context-pack structural checks (human architecture approval still required)`. Any other line starts with `FAIL:`; read it, fix what it names, and run the checker again. The four you are most likely to meet: `FAIL: Unexpected UTF-8 BOM` (the file was saved with a byte-order mark; open it in a plain editor, or rewrite it, and save it as UTF-8 without one); `FAIL: invalid project identifier` (you left the project name empty or wrote a name with a character the checker does not allow; use the form `your-org/your-project`); `FAIL: artifact could not be opened safely: context/<file>` (that file is missing or is not a plain file; copy it again from the starter); `FAIL: invalid frontmatter field: context/<file>` (the lines between the two `---` lines at the top of that file must be exactly the four keys `owner`, `load_when`, `max_length` and `last_verified`; copy the header from the starter). **macOS:** AIDF has not been tested on macOS, and `instantiation/README.md` makes no macOS claim. For a project that already has code, the checker is expected to print `FAIL: platform cannot bind Git validation to the project root`, because it needs Linux or Windows for that case (this comes from reading its source, not from a run). Run the checker on a Linux or Windows machine, or have the Architect check the files by hand against the playbook. For a new project (no code yet) the checker is expected to work on macOS, but that has not been tried; if it fails, treat it as untested and use a Linux or Windows machine.
5. **Write the content.** Each Markdown file in `context/` except `repository-map.md` says "To be written by you (the Architect)" and what belongs in it (`repository-map.md` is the file the script fills; `pattern-registry.json` stays as shipped until the Architect ratifies a pattern). The checker passing means the files have the right shape; it does not mean they say anything true. The Architect decides the content: for a new project follow `instantiation/bootstrap-new.md` steps 3 and 4, for an existing project `instantiation/onboard-existing.md` steps 3 and 4. An agent may draft; the Architect approves, and does not self-ratify a pattern the code merely repeats. Run the checker again after you edit.
6. **Commit** `docs/AIDF-ROLES.md`, `project-context-pack.json` and `context/`.

## Step 5. Record how your agent may work

**What a mode is.** AIDF does not trust an agent because of its name. Each *task* is given a *mode*, which says what the agent may do without stopping and what it must hand back (`modes/execution-modes.md`). The same model can work in one mode on one task and another on the next. There are four modes:

| Mode | Use it when | What the agent may do | What it must not do |
|---|---|---|---|
| **M0 Constrained execution** | The change is a known transform that a machine can check: formatting, a mechanical rename, regenerating generated code. | Apply the transform to the files in scope. | Anything that needs judgment. |
| **M1 Supervised implementation** | You have an *established* Task Contract (approved by a human where the class needs it) and want the change built. This is the normal mode for writing code and tests. | Build the change within the contract; produce the change and the evidence pack. | Create new abstractions, change contracts, or go beyond the declared scope: it stops and says so. |
| **M2 Design and synthesis** | You want options, a plan, tradeoffs or a draft decision record before anything is decided. A spec tool's planning step is the kind of work M2 describes. | Produce plans, options and drafts as files. | Merge anything, or make the decision. It proposes; a human decides. |
| **M3 Adversarial verification** | You want someone to try to break a finished change. | Read the requirement, the diff and the tests; produce findings. | Fix what it finds, or change source: that would be reviewing its own work. |

**The one rule to remember.** On a T2 or T3 change, the session that built it (M1) may not be the only reviewer (M3) of its own work. A second, separate session satisfies it (`core/02-authority.md` section 3); that session may use another tool or model, but changing the model inside the same session does not count. On T3 a third, separate session also acts as security reviewer. On T0 and T1 the same session may check its own work.

**Why you declare.** Until your project has qualified its tool and model (a separate, later step: `profiles/qualification-protocol-v1.1.md`), the Architect *declares* which tool and model may work in which mode, and writes the declaration down. A declaration does not lower any bar: a declared M1 agent still produces the full evidence pack for the class, so a poor declaration shows up as failing checks, not as a merged defect. Keep every declaration: the ones that later fail qualification are useful evidence.

**What to write.** Add a section like this to `docs/AIDF-ROLES.md`, one line per tool and model and mode. These are examples of the shape only; put in your own tools, models and dates.

*Example A: one person, one agent.*

```
Provisional mode declarations (made by the Architect)
2026-11-06 | Tool A with Model X | M1 (implement) for T0 to T3; M2 (plan) for T2 and T3
2026-11-06 | Tool A with Model X, a new session | M3 (review) for T2; for T3 also a third session as security reviewer. Never the session that built the change
```

*Example B: a team with two agents.*

```
Provisional mode declarations (made by the Architect)
2026-11-06 | Tool A with Model X | M1 (implement) and M0 (mechanical changes)
2026-11-06 | Tool B with Model Y | M3 (review) for T2 and T3, as a separate session from the one that built the change
2026-11-06 | Tool B with Model Y | M2 (plan) for T2 and T3
```

*Example C: a team that plans with OpenSpec or Spec Kit.*

```
Provisional mode declarations (made by the Architect)
2026-11-06 | Tool A with Model X, running the OpenSpec or Spec Kit planning step | M2 (plan) only; its apply step is not run until the Task Contract is Approved
2026-11-06 | Tool A with Model X, after approval | M1 (implement)
2026-11-06 | Tool B with Model Y | M3 (review) for T2 and T3, as a separate session from the one that built the change
```

**How to choose.** Start from the work, not from the agent. A mechanical, machine-checkable change is M0. Building to an approved contract is M1. Thinking before deciding is M2. Trying to break finished work is M3. If you are unsure which mode a task needs, pick the one with less freedom: M1 stops at the edge of its contract; M2 and M3 write no source at all.

## Step 6. Start your first change

Classify the change before anything else (`core/01-lifecycle.md` section 6): **T0** mechanical and verifiable by construction (formatting, regenerating generated code, a documentation typo, a mechanical rename); **T1** contained: a behaviour change inside one ownership boundary and within existing contracts, reversible, with the requirement fully clear, using a pattern that is authorised for T1; **T2** structural: it crosses ownership boundaries, changes an interface or contract, is a real design decision, or has meaningful blast radius; **T3** critical: a kernel trip-wire fires (a security boundary, an effect that cannot be undone, high operational or financial consequence). When unsure, take the higher class; going up is free.

If your team plans changes with OpenSpec or Spec Kit, and the change is T2 or T3, run the tool's planning step first, stopping before it builds anything, and only then give the instruction below; `instantiation/spec-tools.md` gives the order and the stop sentence. Otherwise give the instruction as it is.

Give your agent this instruction, with your path and your task in place of the angle brackets:

```
Work under the AI Development Framework (AIDF). Its documents are in <AIDF>. Read KERNEL.md, core/01-lifecycle.md and templates/task-contract.md. Classify this task, write its Task Contract (for T2 or T3 a document that opens with the approver's opening), and stop. Do not change any code until a human has approved the Task Contract. The task: <what you want done>.
```

AIDF does not fix where the files go. Save each Task Contract (and later its evidence pack) in your project, named for the change, for example under `docs/task-contracts/`; commit them, and keep to one place. The *Verifier* named in `core/05-review.md` is the reviewer who checks finished work: a person or a second, separate agent session that did not write it. A review *round* is one pass of that reviewer over the work.

The human at the Architect role then reads the Task Contract and, if it is right, sets its State to Approved with their name and the date. Only after that does the agent implement, then an evidence pack (`templates/evidence-pack.md`) and a separate review (`core/05-review.md`) follow for T2 and T3.

## Then

You are set up. If your team already plans changes with OpenSpec or Spec Kit, continue with `instantiation/spec-tools.md`.

## The script for step 4.3

Copy everything in the box, from `import` to `handle.write(text)`.

```python
import json, re, subprocess
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
raw = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "-z", commit])
paths = [p for p in raw.decode("utf-8").split("\0") if p]
with open("project-context-pack.json", encoding="utf-8") as handle:
    manifest = json.load(handle)
manifest["entry_path"] = "existing"
manifest["source_commit"] = commit
manifest["repository_map"] = {"source_commit": commit, "paths": paths}
with open("project-context-pack.json", "w", encoding="utf-8", newline="\n") as handle:
    json.dump(manifest, handle, indent=2)
    handle.write("\n")
with open("context/repository-map.md", encoding="utf-8") as handle:
    text = handle.read()
text = re.sub(r"(?m)^Source commit: .*$", "Source commit: " + commit, text)
inventory = "<!-- AIDF-TREE-BEGIN -->\n" + "".join(p + "\n" for p in paths) + "<!-- AIDF-TREE-END -->"
text = re.sub(r"<!-- AIDF-TREE-BEGIN -->.*<!-- AIDF-TREE-END -->", lambda match: inventory, text, flags=re.S)
with open("context/repository-map.md", "w", encoding="utf-8", newline="\n") as handle:
    handle.write(text)
```
