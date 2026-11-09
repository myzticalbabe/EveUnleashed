"""paste_browser.py -- browser-driven LinkedIn paste via saved session (v3).

Usage: python paste_browser.py <markdown-file> [--state PATH] [--headed]
       python paste_browser.py --verify-only <probe-file> [--state PATH]
Pipeline (brick guarantee): the caller dry-runs first; this script executes
and VERIFIES. Exit 0 only on probe-found-live. Exit 1 = blocked/failed/
unverified. Screenshots only on failure. Secrets never printed.

FORENSIC FIXES v3 (2026-11-09 -- v2 declared a false platform gate):
- F1 author surface: verify on the author's /recent-activity/all/ page,
  NEVER on the home feed (Top-sort hides own posts; the feed check was the
  liar that enshrined a falsehood in commit 12eeae8).
- F2 unfiltered traffic: capture ALL voyager/api XHR during submit, not an
  endpoint allowlist (the v2 allowlist missed the real submit path and
  reported "zero calls" while the post went through).
- F3 --verify-only mode: the verifier runs standalone with no posting, so
  the fix itself is testable without side effects.
- F4 absence rule: a "not posted / gated" verdict requires BOTH the author
  surface check AND the traffic capture. One negative never closes it.

Slug resolution: no hardcoded profile -- read from the feed's left-rail
/in/ link, so this works for any session owner.
"""

import sys

from playwright.sync_api import sync_playwright

STATE = "C:/Azazael/eve-linkedin-state.json"
FEED = "https://www.linkedin.com/feed/"


def clean(text):
    lines = text.strip().splitlines()
    if lines and lines[0].lstrip().startswith("#") and "DRAFT" in lines[0].upper():
        lines = lines[1:]
    return "\n".join(lines).strip()


def resolve_slug(pg):
    me = pg.evaluate(
        "() => { const a = document.querySelector('a[href*=\"/in/\"]');"
        " return a ? a.href : null; }")
    if not me:
        raise RuntimeError("could not resolve own profile slug from feed")
    return me.split("?")[0].rstrip("/")


def verify_on_author_surface(pg, slug, probe, timeout_ms=8000):
    """Return True iff probe text is found on the author's activity page."""
    pg.goto(slug + "/recent-activity/all/", timeout=60000)
    pg.wait_for_timeout(timeout_ms)
    body = pg.content()
    if probe[:40] in body:
        return True
    pg.goto(slug + "/", timeout=60000)
    pg.wait_for_timeout(timeout_ms)
    return probe[:40] in pg.content()


def verify_only(state, md_path):
    with open(md_path, encoding="utf-8") as f:
        probe = " ".join(clean(f.read()).splitlines()[0:2])[:80]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(storage_state=state)
        pg = ctx.new_page()
        try:
            pg.goto(FEED, timeout=60000)
            pg.wait_for_timeout(4000)
            if "login" in pg.url or "authwall" in pg.url:
                print("BLOCKED: session landed on login/authwall")
                return 1
            slug = resolve_slug(pg)
            print("author slug:", slug)
            if verify_on_author_surface(pg, slug, probe):
                print("VERIFIED: probe found on author surface")
                return 0
            print("ABSENT: probe not on author surface (one negative, not a verdict)")
            return 1
        finally:
            b.close()


def paste(state, md_path, headed):
    with open(md_path, encoding="utf-8") as f:
        text = clean(f.read())
    probe = " ".join(text.splitlines()[0:2])[:80]
    print("paste: %d chars; probe=%r" % (len(text), probe))
    calls = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=not headed)
        except Exception as e:
            print("chrome channel failed (%s); trying default" % str(e)[:120])
            browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context(storage_state=state)
        pg = ctx.new_page()
        # F2: unfiltered -- every voyager/api XHR, any endpoint.
        pg.on("response",
              lambda r: calls.append((r.status, r.url))
              if "/voyager/api/" in r.url else None)
        try:
            pg.goto(FEED, timeout=60000)
            pg.wait_for_timeout(4000)
            if "login" in pg.url or "authwall" in pg.url:
                print("BLOCKED: session landed on login/authwall; refresh state file")
                return 1
            start = pg.get_by_role("button", name="Start a post")
            start.wait_for(timeout=30000)
            start.click()
            box = pg.locator('div[role="textbox"], div.ql-editor').first
            box.wait_for(timeout=20000)
            box.click()
            for i in range(0, len(text), 400):
                box.type(text[i:i + 400], delay=5)
            pg.wait_for_timeout(2000)
            post = pg.get_by_role("button", name="Post", exact=True)
            post.wait_for(timeout=20000)
            for _ in range(30):
                try:
                    if post.is_enabled():
                        break
                except Exception:
                    pass
                pg.wait_for_timeout(1000)
            else:
                print("BLOCKED: Post button never enabled; content rejected pre-submit")
                return 1
            post.scroll_into_view_if_needed()
            pg.wait_for_timeout(800)
            post.click()
            pg.wait_for_timeout(12000)
            writes = [(s, u) for s, u in calls if "contentcreation" in u or "shares" in u
                      or "ugc" in u.lower() or "updates" in u]
            print("voyager XHR total=%d; write-shaped=%d" % (len(calls), len(writes)))
            for s, u in writes[:10]:
                print("  ", s, u[:160])
            try:
                print("toasts:", pg.locator("[role=status], .artdeco-toast-item").all_inner_texts())
            except Exception as e:
                print("toast read err:", str(e)[:150])
            # F1: author surface, never the feed.
            slug = resolve_slug(pg)
            if verify_on_author_surface(pg, slug, probe):
                print("POSTED+VERIFIED: probe found on author surface")
                return 0
            print("UNVERIFIED on author surface after Post (see traffic above)")
            try:
                pg.screenshot(path="/tmp/lipaste_fail.png")
                print("screenshot: /tmp/lipaste_fail.png")
            except Exception:
                pass
            return 1
        except Exception as e:
            print("FAILED: %s" % str(e)[:300])
            try:
                pg.screenshot(path="/tmp/lipaste_fail.png")
                print("screenshot: /tmp/lipaste_fail.png")
            except Exception:
                pass
            return 1
        finally:
            browser.close()


def main(argv):
    args = list(argv)
    headed = "--headed" in args
    args = [a for a in args if a != "--headed"]
    state = STATE
    positional = []
    i = 0
    verify = "--verify-only" in args
    args = [a for a in args if a != "--verify-only"]
    while i < len(args):
        if args[i] == "--state" and i + 1 < len(args):
            state, i = args[i + 1], i + 2
        elif args[i].startswith("--"):
            i += 1
        else:
            positional.append(args[i])
            i += 1
    if not positional:
        print("usage: paste_browser.py [--verify-only] <markdown-file> [--state PATH] [--headed]")
        return 2
    if verify:
        return verify_only(state, positional[0])
    return paste(state, positional[0], headed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
