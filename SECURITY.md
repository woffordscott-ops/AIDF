---
owner: framework-maintainer
load_when: reporting a security problem in this repository
max_length: 1 page
last_verified: 2026-10-27
---

# Security

## Reporting a problem

Email **woffordscott@gmail.com** with the subject line `AIDF security`. There is no public issue tracker yet, so please do not post details publicly before the maintainer has replied.

Include what you found, where (file and commit), how to reproduce it, and the impact you expect. A secret or personal data found in the repository or in the evidence archives counts: say where it is and do not copy it further.

## What is in scope

- The checkers and scripts (`instantiation/`, `verification/`, the pipeline scripts): code that could be made to run attacker-chosen code, read or write outside its workspace, or pass a check it should fail.
- Committed secrets, credentials, or personal data, including in the evidence archives.
- A defect in the framework documents that would make a project following them unsafe (for example a trip-wire that does not fire where the text says it does).

Out of scope: weaknesses in a project that uses the framework, in the model or agent tools it runs on, or reports that need a change to the framework's stated limits (the documents list those).

## What to expect

This is maintained by one person without a service-level agreement. You should get an acknowledgement; there is no guaranteed time. Fixes go through the review process in `core/05-review.md`.
