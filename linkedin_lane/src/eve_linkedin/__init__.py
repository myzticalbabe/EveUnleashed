"""eve_linkedin -- quarantined LinkedIn paste lane.

Publishes via the saved browser session (eve-linkedin-state.json: li_at +
JSESSIONID cookies), stdlib only (urllib). Quarantined OUTSIDE mcml/ like the
NPU lane: third-party surface, declared blast radius.

CLI:  eve-linkedin-paste <markdown-file> [--state PATH] [--dry-run|--live]
Default is --dry-run: builds the exact Voyager request, prints its SHAPE with
secrets redacted, touches nothing. --live performs the POST.
Exit 0 = pasted (live) or would-paste (dry-run). Exit 1 = blocked (no session,
bad state, network/refusal). Exit 2 = usage error.

Secrets discipline: cookie VALUES never hit stdout, logs, or reports. Only
names and lengths are ever printed.
"""

import json
import sys
import urllib.request
import urllib.error

VOYAGER_SHARES = "https://www.linkedin.com/voyager/api/contentcreation/normShares"
VOYAGER_ME = "https://www.linkedin.com/voyager/api/me"


def load_session(state_path):
    with open(state_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    jar = {}
    for c in st.get("cookies", []):
        if c.get("domain", "").endswith("linkedin.com") and c.get("name"):
            jar[c["name"]] = c.get("value", "")
    missing = [k for k in ("li_at", "JSESSIONID") if not jar.get(k)]
    return jar, missing


def csrf_token(jar):
    raw = jar["JSESSIONID"].strip('"')
    # Stored value is usually already "ajax:<id>"; prepend only if bare.
    return raw if raw.startswith("ajax:") else "ajax:" + raw


def base_headers(jar):
    return {
        "Accept": "application/json",
        "csrf-token": csrf_token(jar),
        "X-RestLi-Protocol-Version": "2.0.0",
        "X-Li-Track": '{"clientVersion":"1.0"}',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": "; ".join("%s=%s" % (k, v) for k, v in sorted(jar.items())),
    }


def fetch_owner_urn(jar, timeout=30):
    """Read-only GET /voyager/api/me; derive the shares owner URN. No writes."""
    req = urllib.request.Request(VOYAGER_ME, headers=base_headers(jar), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        me = json.loads(r.read().decode("utf-8", "replace"))
    mp = me.get("miniProfile", {}) or {}
    obj = mp.get("objectUrn", "")  # urn:li:member:<id>
    mid = obj.rsplit(":", 1)[-1] if obj else str(me.get("plainId", ""))
    if not mid:
        raise ValueError("no member id in /me response keys=%s" % sorted(me.keys()))
    return "urn:li:person:" + mid


def build_request(text, jar, owner):
    """Shape the Voyager normShares POST. Returns (url, headers, payload).

    header values are real (needed for --live); callers MUST redact on print.
    """
    payload = {
        "owner": owner,
        "commentary": {"text": {"text": text}},
        "lifecycleState": "PUBLISHED",
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = dict(base_headers(jar))
    headers["Content-Type"] = "application/json"
    return VOYAGER_SHARES, headers, body


def redact(headers):
    out = {}
    for k, v in headers.items():
        if k.lower() in ("cookie", "csrf-token"):
            out[k] = "<redacted len=%d>" % len(v)
        else:
            out[k] = v
    return out


def post_live(url, headers, body, timeout=30):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace")
    except OSError as e:
        return -1, "network: %s" % e


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    live = "--live" in args
    args = [a for a in args if a not in ("--live", "--dry-run")]
    md_path, state_path = None, "C:/Azazael/eve-linkedin-state.json"
    i = 0
    while i < len(args):
        if args[i] == "--state" and i + 1 < len(args):
            state_path, i = args[i + 1], i + 2
        elif not md_path:
            md_path, i = args[i], i + 1
        else:
            i += 1
    if not md_path:
        print("usage: eve-linkedin-paste <markdown-file> [--state PATH] [--dry-run|--live]")
        return 2
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except OSError as e:
        print("cannot read %s: %s" % (md_path, e))
        return 2
    jar, missing = load_session(state_path)
    print("session: %d linkedin cookies" % len(jar))
    if missing:
        print("BLOCKED: session missing %s; re-login and refresh %s" % (missing, state_path))
        return 1
    try:
        owner = fetch_owner_urn(jar)
    except Exception as e:
        print("BLOCKED: owner lookup failed: %s" % str(e)[:200])
        return 1
    url, headers, body = build_request(text, jar, owner)
    shape = {"url": url, "owner": owner, "headers": redact(headers),
             "payload_keys": sorted(json.loads(body.decode()).keys()),
             "text_chars": len(text)}
    print("request shape: %s" % json.dumps(shape))
    if not live:
        print("DRY-RUN: nothing posted. Re-run with --live to paste.")
        return 0
    status, resp = post_live(url, headers, body)
    print("live POST status=%s resp=%s" % (status, resp[:500]))
    return 0 if status in (200, 201) else 1


if __name__ == "__main__":
    sys.exit(main())
