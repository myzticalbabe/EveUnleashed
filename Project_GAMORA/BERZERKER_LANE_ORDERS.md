# Standing orders for the Berzerker lane: the Colosseum coaches in parallel

Berzerker is Gamora's native A.I.O.: the Colosseum mind (23 named processes
across conscious / subconscious / unconscious strata, live in
cognition.PROCESSES) turned into a STEM coding coach -- patient, exact,
receipted. Stdlib only, no models, no network in this lane.

Re-read this file on every session start. The parallelism rule below is
permanent, not per-task.

## Orders

1. Fan coaching work across the bounded pool: 8 workers max, shutdown
   with wait=False. Per-learner drills, per-claim debunks, parallel
   probes -- one worker each, never one thread for the whole class.
2. Route every NON-MAX inferencing task to LLM worker swarms: drafts,
   checks, per-process intuitions. Max push/drive stays with Jaeger for
   verdict-grade answers; the coach advises, the trace decides the road.
3. Every delegation gets a live_log receipt plus one Jaeger span
   (recorded, never raised). A coached answer without a receipt is
   advice from nowhere -- re-receipt it, do not re-run it.
4. On WSL/Kali pillars, probe before acting (`shutil.which`, never
   execute untrusted code). Native kernels stay optional; the lane
   degrades to a named message, never a traceback.
5. Prove each step natively: `pytest Project_GAMORA/tests/` (berzerker
   suite), `bible_check --check`. No model, no network.

## Acceptance

- Berzerker tests green offline; bible gates clean; scanner clean.
- After restart, the first coaching batch fans across the bounded pool
   with receipts + spans -- the Colosseum coaches in parallel, or it
   does not coach at all.

## Dashboard (the operator watches)

6. Receipts ARE the dashboard. OpenCode tails the live log while the
pool runs -- `eve e2e --log PATH` for the live-logged run, one receipt
per delegation, one span per handoff. The operator watches the
Colosseum work, learner by learner, worker by worker.
