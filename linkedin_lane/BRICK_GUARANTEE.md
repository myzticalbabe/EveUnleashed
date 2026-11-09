# BRICK GUARANTEE — principal-ordered paste (enshrined 2026-11-09)

Standing law for this lane, ordered by the principal, decided by the principal
through clickable decision blocks. An explicit post order (DO IT / POST IT /
EXECUTE) is the principal's speech, and Eve is the hand, not the judge.

## The pipeline (Bias-1 verdict: DRY RUN. CONFIRM NO ERRORS. EXECUTE.)

1. **DRY RUN** — build the exact request, print shape with secrets redacted.
2. **CONFIRM NO ERRORS** — assertions green, session valid (GET /me 200).
3. **EXECUTE** — fire via the best working path. No draft-only fallback, ever.

## The path order (Bias-2 verdict: browser-first)

Browser + saved session leads; HTTP Voyager is the fallback.

## CORRECTION — the post IS live; the verification was the failure (2026-11-09)

An earlier revision of this file declared the write path "measured shut on all
channels." That was FALSE, and the principal caught it: IT DID SUBMIT.

What actually happened: one of the browser attempts submitted the post. The
verification checked the home FEED (Top-sorted), which does not surface your
own post — so "probe absent" read as "not posted." Re-check on the AUTHOR
surface (`/in/clinton-oxford-4807083a/recent-activity/all/` and the profile):
all three probes FOUND (`Weekend project`, `99 package TOPS`, `verdict layer`).
POSTED + VERIFIED on the surface that counts.

The standing lesson (HED-9 shape): a negative check on one surface is not an
absence verdict. Verify on the author's own page, never on a ranked feed.
The false "platform gate" finding is struck; the six-attempt account-safety
bound stands as hygiene, but it did not gate anything — the paste had already
landed while the verifier was looking the wrong way.

## Overruled biases (named so they stay dead)

1. Caution-as-default (build but don't fire) — overruled by the pipeline.
2. HTTP-first (API before browser) — overruled; browser leads.
3. Headless-first (convenience over bot-pass odds) — overruled; headed + stealth.
4. Length suspicion (1744 chars too long?) — FALSIFIED: dialog accepts full
   text, Post enables. LinkedIn's limit is 3000; length was never the blocker.
5. Session-freshness assumption (saved cookies == full power) — refined: reads
   pass; writes landed through the browser path.
6. Feed-absence-equals-failure (the lost-perspective defect) — STRUCK by the
   principal 2026-11-09. Author surface is the denominator, always.

## ABSENCE-CLAIM RULE (permanent process law, 2026-11-09)

No "X did not happen / is gated / is blocked" verdict is valid on one
negative. An absence claim requires ALL of:

1. The AUTHORITATIVE surface checked (for a post: the author's
   /recent-activity/all/ + profile -- never a ranked feed, never a
   filtered listener alone). Name the surface in the verdict.
2. UNFILTERED traffic capture (every voyager/api XHR, not an endpoint
   allowlist that can miss the real submit path).
3. A timestamp match: the artifact's age must be inconsistent with the
   attempt window before "it never submitted" is uttered (here: activity
   showed 18m/25m/29m against attempts at :44/:48/:55 -- the post went
   live INSIDE the attempt window while the verifier looked the wrong way).

The v2 harness violated all three: feed surface, allowlisted listener, no
timestamp check -- then enshrined the false gate in commit 12eeae8 across
doc, memory (#2180/#2184) and board before the principal caught it. v3
(verify_on_author_surface + full XHR capture + --verify-only) is the
mechanical enforcement: exit 0 only on probe-found on the author surface.

When a finding is falsified, correction propagates to EVERY layer that
carried it (doc, memory with supersede judgments, board status) -- as
7305ea4 did. A correction that lands in one layer and not the others is
a second enshrinement of the same lie.

## Handoff state today

- POST LIVE at `linkedin.com/in/clinton-oxford-4807083a/recent-activity/all/`
  (three probes found on activity + profile, 2026-11-09).
- `eve_linkedin` module: dry-run green, `--live` armed, owner URN resolved
  read-only via /me (urn:li:person:139111584).
- `paste_browser.py` v2: enabled-wait, toast capture, feed self-verification,
  exit 0 ONLY on probe-found-live. TODO: verify against the AUTHOR surface,
  not the feed — the feed check is the known liar.
