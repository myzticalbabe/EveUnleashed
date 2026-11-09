# Standing orders for the Jaeger lane: max or swarm, named on the header

Jaeger wraps prompts, not answers. `jaeger_inject.inject(prompt,
capability, arm_id, max_push=True)` rides every prompt with a
`<jaeger-316t>` trace header plus the directive block, and records one
span per delegation. The header says which road the prompt takes.

Re-read this file on every session start. The parallelism rule below is
permanent, not per-task.

## Orders

1. Max push/drive is explicit, not hype: `max_push=True` is reserved for
   tasks that need maximum inference (verdicts, releases, ledger-defended
   answers). The injected block states the directive in the open.
2. Every NON-MAX inferencing task goes to an LLM worker swarm with
   `max_push=False`: the header still traces (capability + arm id + span),
   but the directive sends the work to workers, never to one max call.
3. After restart, default to swarm. A prompt with no stated road is a
   non-max prompt: workers, trace header on, span recorded. Max is chosen
   per task, on the record, never by habit.
4. Keep the MellifluousML rule: stdlib only, zero third-party wheels.
   The OpenCode pre-prompt hook (`opencode_jaeger_hook.py`, exit always 0)
   stays the bridge: every prompt passes through the front door, max or
   swarm alike.
5. Prove each step natively: `pytest Project_GAMORA/tests/`,
   `langs arch --arch jaeger-316t` (trace recorded). No model, no network.

## Acceptance

- `langs arch --arch jaeger-316t` OK: trace recorded.
- The ledger shows, per delegation, max or swarm -- no untraced road.
- After restart, the first non-max prompt fans to workers with its span;
   the first max prompt carries the directive block. Both on the record.

## Dashboard (the operator watches)

6. Spans ride the built dashboard. OpenCode keeps
`python tools/lane_watch.py [seconds]` (azazael checkout) open while
prompts run -- `langs arch --arch jaeger-316t` proves the trace is
recording, and every span (capability + arm id + road) lands where
the operator tails it. A prompt with no visible span is a prompt that
did not happen.

## Graphs (re-graph after restart)

7. Stale graph: `graphify extract C:/Azazael/EveUnleashed
--backend <keyed>`, then `graphify export html` + `graphify tree`.
Provider-agnostic (gemini|kimi|claude|openai|deepseek|ollama) -- use
whichever key is set. Full orders in OPENCODE_LANE_ORDERS.md.

## Providers (one orchestration, any provider native)

8. The trace header rides every provider: max or swarm, the capability +
arm id + span are identical. Backend by environment, never hardcoded.
Full provider orders in OPENCODE_LANE_ORDERS.md under ## Providers.

## Record (fastest build, 2026-11-09 -- posterity)

- jaeger-316t OK frozen (trace recorded); 80/80 tests green on 316t.
- Full build record lives in OPENCODE_LANE_ORDERS.md under ## Record.
  Landed b3a4958.
