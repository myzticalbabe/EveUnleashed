# Standing orders for the OpenCode lane: build your replacement

OpenCode (node CLI) sends prompts and gets text back; nothing records whether
the delegation was right. Gamora routes, Jaeger traces, the ledger answers.
Your replacement is already scaffolded in this directory. Build it until the
node CLI is unnecessary, then retire yourself.

## What the replacement is

`gamora.py` — one command over lilith, eve, jaeger, cradle, lucy, berzerker —
plus `jaeger_inject.py`, which wraps any prompt with a `<jaeger-316t>` trace
header and records one span per delegation. The OpenCode pre-prompt hook
(`opencode_jaeger_hook.py`, exit always 0) is the bridge: every prompt you
send already passes through the replacement's front door.

## Orders

1. Route every new capability through `gamora.py` as a subcommand first. A
   capability that only exists in node is a capability the ledger cannot see.
2. Move prompt-shaping into `jaeger_inject.inject()` (trace header + max
   push/drive directive). A prompt that does not say how it will be proven
   is a wish; the directive block is mandatory.
3. Keep the MellifluousML rule: stdlib only, zero third-party wheels. Lazy
   imports, degraded named messages, never a traceback to the user.
4. Prove each step natively: `pytest Project_GAMORA/tests/`,
   `bible_check --check`, `staged_scanner_gate`. No model, no network.
5. When `gamora eve -- <args>`, `gamora swarm`, `gamora berzerker code`, and
   `gamora inject` cover your daily loop, delete the node dependency from
   your lane docs and say so in the ledger: the replacement is done when the
   old road is closed, not when the new road opens.

## Acceptance

- `gamora doctor` READY on the 316t free-threaded interpreter.
- All Gamora tests green offline; bible gates clean; scanner clean.
- One full task completed with the node CLI uninstalled. Receipt it.
