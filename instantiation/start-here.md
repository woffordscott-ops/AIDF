---
owner: framework-maintainer
load_when: a person is starting AIDF in a project for the first time and wants an agent to guide the setup
max_length: 3 pages
last_verified: 2026-11-24
---

# Start here: set up AIDF by pasting one prompt

You have cloned AIDF into a folder named `aidf` next to your project (see "Getting started" in `README.md`). This page gives you one prompt. You open your coding agent in your project folder, paste the prompt, and answer its questions. When it finishes you have: the two roles recorded, a project context pack that the AIDF checker has passed, a record of which agent may work in which mode, and a first Task Contract waiting for your approval.

**What the agent will do.** Read the AIDF setup page, ask you questions one at a time, show you a summary and wait for your "yes", then write the files and run the checker.

**What the agent will not do.** It will not choose who your Change Owner or Architect is, mark anything approved, write down which agents may work in which mode before you confirm each line, change your code, install anything outside your project folder without asking, or commit without asking. The framework keeps those decisions with a human; the agent proposes and you decide.

**A lighter start for a small project.** If you tell it the project is one person's single tool or script, and nothing in the risk question applies, the agent offers to write only three of the context files and to leave the other seven as shipped until the project grows (for a project that already has code, the file list in the repository map is still recorded). You can say no. For a new project it also writes a standing authorization, a record that you sign yourself by editing named lines, which lets your first changes in its scope run under the lighter T1 controls for 90 days; until you sign it the first change is T2. For a project that already has code it does not change how your first change is classified: with no ratified pattern yet it is usually T2.

**What you must still do yourself.** Read the draft context pack and correct it (the checker only tests that the files have the right shape, not that they are true). Approve the first Task Contract if it is right, by opening the file it names and changing the named line yourself; saying yes in chat does not count. Every reply ends with a line telling you the next required step, and the agent shows a checklist of what remains before a change is done. When a T2 or T3 change is built, open a *new* agent session to review it: at those classes the session that built a change may not be its only reviewer (`core/02-authority.md` section 3); a T0 or T1 change may be checked in the same session.

**If you prefer to do it by hand,** or the agent cannot follow the prompt, use `instantiation/set-up-aidf.md`: it is the same steps, written for a person.

## The prompt

Open your agent in your project folder, then paste everything in the box.

```
You are helping me set up the AI Development Framework (AIDF) in my project. This folder is my project. The AIDF documents are in the folder named aidf next to this folder; if you cannot find it, ask me for its path.

Read these in order: aidf/KERNEL.md, aidf/instantiation/set-up-aidf.md, aidf/core/02-authority.md section 1, aidf/templates/task-contract.md. Then do the work of set-up-aidf.md Steps 2 to 6 for me, in the way described below. Step 1 (the clone) is done.

Rules. They apply to every step and override anything that seems to say otherwise.
1. You propose; a human approves. I am the human.
2. Never choose, guess or invent who the Change Owner or the Architect is. Ask me; I may hold both roles.
3. Never set a Task Contract, a context pack or any record to Approved, and never write a name in an "approved by" field. Leave it as pending for me.
4. Never write a mode declaration (which tool and model may work in which mode) that I have not confirmed line by line.
5. Mark every file you write from my answers or from reading my code as "Draft, to be confirmed by the Architect" on its first line after the front matter; where you do not know a fact, write "Unknown: to be decided by the Architect" rather than guessing.
6. Ask one question at a time, wait for my answer, and keep each question short and in plain words. If a term is unfamiliar, explain it in one sentence.
7. Write no file until you have shown me a summary of my answers and I have said yes to it.
8. Use only the commands in set-up-aidf.md; write only inside this project folder; install nothing outside it, and nothing at all, without asking me first; do not commit, merge or push unless I tell you to.
9. On a T2 or T3 change, the session that builds it may not be its only reviewer. When such a change is built, tell me to open a new session for the review; at T0 and T1 the same session may check it (core/02-authority.md section 3).
10. Stop after the first Task Contract is written and shown to me. Do not change any code or start the first change.
11. End every reply with one line, "Next required step: ...", that says what I must do or decide next, and mark anything that is optional as optional. Never leave me to guess what comes next.
12. When you ask me to approve or sign something, give the file, the line and the words to write, and say that approving in chat does not count because the file must change. Never suggest a sed command or any other shell one-liner for this.
13. The first time you ask me for a review, say that review reports and dispositions go in docs/reviews/ in this project unless I choose another place.
14. Put every decision you ask of me in one plain sentence, say what each choice means for me, and put the framework's own term in brackets after it.
15. Offer the lighter start of question g only when I say the project is small and my answer to every part of question f was no. Never apply it unasked. A yes to any part of f cancels it. A change that hits a trip-wire of KERNEL.md is still T3 and a new dependency still needs my approval.

Interview. Ask these, in this order, one at a time:
a. Who is the Change Owner and who is the Architect? (One person can be both.)
b. Is this a new project with no code yet, or an existing project with code? If existing, check that this folder is a Git repository with at least one commit; if not, tell me the command and ask before running it.
c. What is the project's name, and the organisation or owner name to put in the context pack?
d. In a few sentences: what is being built, and for whom?
e. What language and tools does it use, how are its tests run, and what must never break?
f. Does it handle any of these: logins or permissions; secrets or encryption; personal, health or regulated data; money or billing; an API other teams or the public depend on; infrastructure or production settings; deleting or irreversibly changing data? (Note for you, the agent: a "yes" does not by itself make a change T3. KERNEL.md makes a change T3 only when that change hits one of its trip-wires, so use my answers to look closely at each change, not to classify the project.)
g. Only if every part of my answer to f was no: is this a small project, meaning one person, a single tool or script, and nothing that others depend on? If I say yes, offer the lighter start described below (fewer context files to write; it does not change how my first change is classified) and wait for my choice.
h. Which agent tool and model will build changes here, and which will review them? (Review must be a separate session.) Will you plan changes with OpenSpec or Spec Kit?
i. What is the first change you want to make?

Then show me a short summary of my answers and ask me to confirm or correct it. After I say yes:
- Write docs/AIDF-ROLES.md with the two roles from my answers, and a "Provisional mode declarations" section in the form of set-up-aidf.md Step 5. Show me each declaration line and write it only after I confirm it.
- Build the context pack as set-up-aidf.md Step 4 describes: copy the starter, name the project, for an existing project record its files with the script of Step 4.3, run the checker, and write the content of each context file as a draft from my answers and, for an existing project, from reading the code. Show me the checker's result as it is; if it fails, fix the files and run it again, and tell me what you changed.
- If I chose the lighter start, do the context pack this way instead: copy the starter and name the project as before; if the project already has code, record its files with the script of Step 4.3 exactly as in the step above, so that context/repository-map.md is not left as shipped; write drafts of only context/architecture-overview.md, context/testing-strategy.md and context/conventions.md and leave every other context file as shipped, telling me they are to be written when the project has more than one file; run the checker. If the project has no code yet, also write docs/standing-authorization.md from aidf/templates/standing-authorization.md: the pattern described in the authorization itself as "a small single-owner tool of this project" with no registry entry (the checker refuses one in a project with no code), the scope "changes to this project's tool or script", the expiry 90 days from today, the status left Inactive, and the grantor and the date left pending for me to fill by editing those lines; tell me that once I have signed it, changes in that scope may run as T1 (core/01-lifecycle.md section 7, Route 2), that it gives no precedent and lapses at the expiry, and that my first change is T2 until I have signed it. If the project already has code, do not write an authorization, and tell me that the lighter start does not lower the class of my first change: with an empty pattern registry it is classified as core/01-lifecycle.md section 7 says, usually T2.
- Classify my first change as set-up-aidf.md Step 6 and core/01-lifecycle.md say (T0 to T3, against the trip-wires of KERNEL.md; a "yes" to question f does not by itself force T3, but a change that itself hits such a trip-wire does), write its Task Contract in docs/task-contracts/ from aidf/templates/task-contract.md with State Established and the approval fields pending, show it to me, and stop.
- Show me this checklist for the first change, each box ticked or not, and tell me I can ask for it at any time: [ ] the Task Contract is approved by me; [ ] the change is built with its tests; [ ] for T2 or T3, a separate session has reviewed it and passed at a named commit; [ ] the review records are saved in docs/reviews/; [ ] the context pack is read and confirmed by me; [ ] the change is merged; [ ] if a standing authorization was written, it is signed by me.
- End by telling me, in a short list: the files you wrote; what I must read and correct; that the Architect approves the Task Contract by setting its State to Approved with a name and date; and that review of a built T2 or T3 change needs a new session.
```
