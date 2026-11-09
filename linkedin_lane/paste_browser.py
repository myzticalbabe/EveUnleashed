"""paste_browser.py -- browser-driven LinkedIn paste via saved session (v2 evolved).

Usage: python paste_browser.py <markdown-file> [--state PATH] [--headed]
Pipeline (brick guarantee): the caller dry-runs first; this script executes
and VERIFIES -- exit 0 only when the post text is found live on the feed.
Exit 1 = blocked/failed/unverified. Screenshots only on failure.
Secrets never printed.

Evolutions over v1 (headless attempt left dialog open, post absent):
- wait for the Post button to become ENABLED before clicking (v1 clicked blind).
- post-click: wait for dialog detach OR success toast, up to 30 s.
- self-verification: fresh feed load, probe for the draft's opening line.
- strips a leading meta header line (# ... DRAFT ...) -- file notes, not speech.
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


def main(argv):
    args = list(argv)
    headed = "--headed" in args
    args = [a for a in args if a != "--headed"]
    md_path, state = None, STATE
    i = 0
    while i < len(args):
        if args[i] == "--state" and i + 1 < len(args):
            state, i = args[i + 1], i + 2
        elif args[i].startswith("--"):
            i += 1
        elif not md_path:
            md_path, i = args[i], i + 1
        else:
            i += 1
    if not md_path:
        print("usage: paste_browser.py <markdown-file> [--state PATH] [--headed]")
        return 2
    with open(md_path, encoding="utf-8") as f:
        text = clean(f.read())
    probe = " ".join(text.splitlines()[0:2])[:80]
    print("paste: %d chars; probe=%r" % (len(text), probe))
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=not headed)
        except Exception as e:
            print("chrome channel failed (%s); trying default" % str(e)[:120])
            browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context(storage_state=state)
        pg = ctx.new_page()
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
                box.type(text[i:i + 400], delay=2)
            pg.wait_for_timeout(1500)
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
            post.click()
            posted = False
            try:
                pg.wait_for_selector('div[role="dialog"]', state="detached", timeout=30000)
                posted = True
            except Exception:
                try:
                    pg.get_by_text("Post successful", exact=False).wait_for(timeout=10000)
                    posted = True
                except Exception:
                    pass
            if not posted:
                print("UNCERTAIN: no close/toast after Post; verifying on feed anyway")
            # Self-verification: fresh feed load, probe for our text.
            pg.goto(FEED, timeout=60000)
            pg.wait_for_timeout(7000)
            body = pg.content()
            if probe[:40] in body:
                print("POSTED+VERIFIED: probe found live on feed")
                return 0
            print("UNVERIFIED: probe absent from feed after Post")
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
