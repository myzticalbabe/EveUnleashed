# Standing orders for the Lucy lane: the swarm judges, the script grounds

Lucy answers offline: `lucy.companion_response(mood, note)` returns the
grounding script, never a model call. The `therapy_prompt` in the same
return is the question a caller WITH a swarm may ask. Lucy never requires
a swarm; she always tells the swarm what to ask.

Re-read this file on every session start. The parallelism rule below is
permanent, not per-task.

## Orders

1. Keep `response` model-free forever: Eliza reading + offline grounding
   script. No network, no model, no audio hardware in this lane.
2. Route every NON-MAX inferencing task to an LLM worker swarm through
   `therapy_prompt`: per-candidate replies, per-mood probes, draft
   phrasings. One worker per candidate; the swarm asks, the script grounds.
3. The arena runs its five judges (rock, paper, scissors, lizard, spock)
   in fixed throw order with a disclosed seed. Fixed order, fixed judges,
   no editorial discretion -- parallelism fans candidates, never judges.
4. Max push/drive is not Lucy's road. A task that needs maximum inference
   leaves this lane for Jaeger (`max_push=True`) with the trace header on;
   Lucy records the handoff in the ledger, she does not upgrade herself.
5. Prove each step natively: `pytest Project_LUCY/tests/`, `bible_check
   --check`. No model, no network.

## Acceptance

- `langs arch --arch lucy` OK: grounding present.
- All Lucy tests green offline; bible gates clean.
- After restart, the first reply still carries the grounding script and
   the swarm prompt -- the lane answers the same on workers or alone.

## Dashboard (the operator watches)

6. Every judged reply is observed. OpenCode opens the watch surface
with the run: the five-gate verdict (one line per throw, fixed order)
plus `eve e2e --log PATH` for the live-logged run the operator tails.
A judgement with no open log is an unobserved judgement.
