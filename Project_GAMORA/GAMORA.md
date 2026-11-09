# PROJECT GAMORA -- Gamora DOMellifluousML Berzerker A-I-O cliT

One command over parts that existed and did not know about each other.

| part | where it lives | what Gamora does with it |
| --- | --- | --- |
| **Lilith swarm / Spitfire** | `scripts/lilith_live_monitor.py`, `src/spitfire/`, `src/eve_unleashed/swarm_oracle.py` | `gamora lilith` reads hive status; `gamora swarm` fans claims natively |
| **Eve Unleashed** | `src/eve_unleashed/cli.py` | `gamora eve -- <args>` passes through; Eve runs |
| **Jaeger 3:16T** | `src/AOA/core/delegation_tracer.py` + `src/CORE/cd3_exporter.py` | every injection writes one span; `gamora inject` wraps any prompt |
| **Cradle** | `Project_CRADLE/cradle.py` | `gamora cradle -- <args>` passes through |
| **Lucy** | `Project_LUCY/lucy.py` | `gamora lucy <mood> [note]` -- Eliza + therapy, offline-first |
| **Berzerker A.I.O.** | `Project_GAMORA/berzerker.py` (mind over `src/eve_unleashed/cognition.py`, `intuition.py`) | `gamora berzerker audit` (23-process census) / `mind <request>` (3-strata crossing) / `code <assignment> [--lang] [--level]` (STEM coach for girls, offline-first) |

## Why a harness and not a merge

The parts keep their paths because gates, docs, and the graph quote
those paths. Gamora is the front door: one file to run, one doctor to
trust, and the machinery where the gates already point. It adds no
judgement of its own -- only routing plus one Jaeger span per
delegation, so "was this the right choice" stays answerable from the
ledger.

## Commands

    python gamora.py doctor
    python gamora.py lilith [--once]
    python gamora.py eve -- <eve args>
    python gamora.py cradle -- <cradle args>
    python gamora.py lucy <mood> [note] [--json]
    python gamora.py berzerker audit | mind "<request>" | dream [host]
    python gamora.py berzerker inhibited <host> | weird [--lang L]
    python gamora.py berzerker code "<assignment>" [--lang L] [--level spark|builder|pilot] [--name Ada] [--json]
    python gamora.py berzerker done --name Ada --level spark   # tally one finished session (3 earn the next rung)
    python gamora.py doctor [--json]
    python gamora.py swarm <claim> [...]
    python gamora.py inject "prompt" [--capability C --arm A]

Requires the 316t free-threaded interpreter
(`C:/Azazael/.venvs/py316t/Scripts/python.exe`). `doctor` exits 1
without it.

## OpenCode evolution: Jaeger 3:16T prompt injectors

`jaeger_inject.py` is the OpenCode CLI evolved: same prompt in, plus a
`<jaeger-316t trace_id=... span_id=...>` header, the max push/drive
directive block, and one span in the tree's own ledger. The span write
never fails the prompt (header-only degradation).

Bridge into OpenCode/Kilo through the front door (verified 2026-11-09:
opencode core has no `hooks.pre-prompt` config key, so no dead config is
written -- routing IS the wire):

    gamora eve -- <args>    # Eve runs, one eve.run span per delegation
    gamora kilo -- <args>   # Kilo runs, one kilo.run span per delegation
    gamora inject "prompt"  # header + span, pipe into any CLI

Or pipe by hand: `echo "prompt" | python opencode_jaeger_hook.py | kilo run`
(the hook is a stdin/stdout filter, exit always 0). Every delegation
through these doors carries a Jaeger span in the tree's own ledger.
