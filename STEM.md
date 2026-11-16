# STEM learning guide — EveUnleashed

EveUnleashed is the all-in-one native runtime for Gamora, Lucy, Jaeger and Berzerker, built for free-threaded Python.

This guide is for teachers, mentors, club leaders, parents and students who want to
use this repository as a vehicle for real STEM learning — in particular for girls and
other groups still under-represented in computing, engineering and mathematics. It
says what the project actually teaches, how to run a session with it, and what to
remove so that nobody is excluded by accident.

## What this project teaches

**Subject areas**

- free-threading and concurrency
- local inference
- process and resource monitoring
- user-interface design

**Skills practised**

- measuring a speed-up instead of assuming one
- reasoning about shared state without a global lock
- reading a system monitor honestly

## Prerequisites

Python 3.13 or newer. The free-threaded build is the target, but the exercises run on a standard interpreter too.

Nothing else is assumed for the entry-level activity below: no prior programming
experience, no particular hardware, and no home internet connection.

## Six practices this repository is set up to support

These follow the published guidance on gender-equitable STEM education — connect the
work to learners' lives, let them investigate real problems, treat struggle as part of
the work, name and challenge stereotypes, make the work collaborative, and put
learners in front of diverse role models.

1. **Connect it to their lives.** why an app freezes while it works, and what 'using all the cores' actually means
2. **Let them investigate.** give the group one task run sequentially and then in threads, and ask them to predict both timings first
3. **Make struggle normal.** Build the session so that the first attempt is *expected*
   to fail. Say out loud that debugging is the subject, not a penalty. Ask "what did
   that error tell you?" before offering the answer.
4. **Challenge the stereotype.** Name who does this work and why it is not a gendered
   skill. Praise the method ("you isolated the variable"), not the person ("you're a
   natural") — the second kind of praise teaches learners that ability is fixed.
5. **Make it social.** pairs split into 'measure' and 'explain'; the explainer sees only the numbers, not the code
6. **Show diverse role models.** concurrency researchers and the engineers who made multi-threaded runtimes usable

## A 90-minute session

1. *(15 min)* Time one task on one thread, then on four.
2. *(25 min)* Predict the speed-up, then measure it, then explain the gap.
3. *(35 min)* Introduce shared state and find a race by running repeatedly.
4. *(15 min)* Fix it and prove the fix under repetition.

## Vocabulary to define before the session

Specialist vocabulary is a hidden entry test if nobody explains it. Define each of
these the first time it appears, in one sentence, in the learners' own words:

1. **thread** — one path of execution inside a process.
2. **GIL** — the lock that serialises much of CPython.
3. **race condition** — a result that depends on timing.

## Accessibility

Read [ACCESSIBILITY.md](ACCESSIBILITY.md) before running a session. Two rules matter
most in a mixed-ability room:

- Every activity must be completable with a keyboard alone, with a visible focus ring.
- Every instruction names the control or the heading ("the **Run** button in the
  toolbar"), never a colour or a position.

Pair learners rather than singling anyone out, and always offer a text-only route for
a visual step.

## Contributing as a learner

Small, well-scoped contributions are the point, not a consolation prize:

- Browse issues labelled
  [`good first issue`](https://github.com/myzticalbabe/EveUnleashed/labels/good%20first%20issue).
- Read [CONTRIBUTING.md](CONTRIBUTING.md) — it has a section written for first-time
  contributors.
- Ask in [SUPPORT.md](SUPPORT.md) if anything is unclear. Asking is expected here; it
  is not a failure.

## Licence and classroom reuse

Classroom, club and workshop use is welcome. See `LICENSE` for the exact terms, and
check whether your institution requires a separate agreement before redistributing
modified copies.
