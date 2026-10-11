"""Poster for ShortbusShawties (Short Bus Shawties group-chat page).

Normal mode (hourly via GitHub Actions):
  Two posting windows per day, Pacific time: slot a 12:00-15:59, slot b 20:00-23:59.
  Each window posts exactly once. If a window is already done, the run exits.
  Content source, in order: next unused file in queue/ (q01.json, q02.json, ...),
  then the reserve in data/bank.json (recycled if exhausted).

Seed mode (SEED=1, manual one-time run): posts data/seed.json in REVERSE order with a
  gap between posts so the profile grid opens with the first seed item at the top-left.

Env: IG_ACCESS_TOKEN (required unless DRY_RUN), IG_HANDLE, IG_NAME,
     FORCE=1 (manual: ignore the time windows), DRY_RUN=1 (render only), SEED=1, SEED_GAP=seconds.
"""
import glob, json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from render_humor import render_post  # noqa: E402

API = "https://graph.instagram.com"
TZ = ZoneInfo("America/Los_Angeles")
now = datetime.now(TZ)
TODAY = now.strftime("%Y-%m-%d")
HANDLE = os.environ.get("IG_HANDLE") or "@shortbusshawties"
NAME = os.environ.get("IG_NAME") or "ShortbusShawties"
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
FORCE = os.environ.get("FORCE") == "1"
DRY = os.environ.get("DRY_RUN") == "1"
SEED = os.environ.get("SEED") == "1"
SEED_GAP = int(os.environ.get("SEED_GAP") or "180")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
from common import schedule  # noqa: E402
SLOTS = schedule()  # learned posting windows (data/schedule.json); defaults a 12-14, b 20-22 PT


def log(*a):
    print(f"[{datetime.now(TZ):%H:%M:%S}]", *a, flush=True)


def sh(*cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def git_push(paths, msg):
    sh("git", "config", "user.name", "shortbus-bot")
    sh("git", "config", "user.email", "shortbus-bot@users.noreply.github.com")
    sh("git", "add", *paths)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        sh("git", "commit", "-m", msg)
    for attempt in range(4):
        try:
            sh("git", "pull", "--rebase", "-q")
            sh("git", "push", "-q")
            return sh("git", "rev-parse", "HEAD")
        except subprocess.CalledProcessError as e:
            log("push retry", attempt, e.stderr)
            time.sleep(5)
    raise SystemExit("git push failed")


def api(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params)
    if method == "GET":
        req = urllib.request.Request(f"{API}/{path}?{data}")
    else:
        req = urllib.request.Request(f"{API}/{path}", data=data.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(TOKEN, "***") if TOKEN else ""
        raise SystemExit(f"Instagram API error {e.code} on {path}: {body}")


def url_ok(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
            return r.status == 200 and "image" in r.headers.get("Content-Type", "")
    except Exception:
        return False


def public_urls(rel_paths, sha):
    urls = []
    for p in rel_paths:
        cands = [f"https://raw.githubusercontent.com/{REPO}/{sha}/{p}",
                 f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{p}"]
        chosen = None
        for _ in range(12):
            chosen = next((u for u in cands if url_ok(u)), None)
            if chosen:
                break
            time.sleep(5)
        if not chosen:
            raise SystemExit(f"Image never became publicly reachable: {p}")
        urls.append(chosen)
    return urls


def wait_ready(cid):
    for _ in range(30):
        st = api("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Container {cid} failed: {st}")
        time.sleep(5)
    raise SystemExit(f"Container {cid} not ready in time")


def used(field):
    ids = set()
    for f in glob.glob(os.path.join(ROOT, "posted", "*.json")):
        with open(f) as fh:
            v = json.load(fh).get(field)
        if v:
            ids.add(v)
    return ids


def load(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def build_caption(it):
    return it.get("caption") or ("send this to the group chat that needs it \U0001F480\n\n"
                                 "#groupchat #darkhumor #memes #relatable #funny")


def sane(it):
    try:
        ms = it["messages"]
        return it.get("format", "chat") == "chat" and 3 <= len(ms) <= 10 and all(m.get("from") and m.get("text") for m in ms)
    except Exception:
        return False


def next_item():
    done = used("queue_id")
    for f in sorted(glob.glob(os.path.join(ROOT, "queue", "*.json"))):
        qid = os.path.splitext(os.path.basename(f))[0]
        if qid not in done:
            try:
                with open(f) as fh:
                    it = json.load(fh)
            except Exception:
                log("skipping unreadable queue file", qid); continue
            if not sane(it):
                log("skipping malformed queue file", qid); continue
            it.setdefault("id", qid)
            return it, "queue", qid
    bank = load("data/bank.json")
    spent = used("bank_id")
    for it in bank:
        if it["id"] not in spent:
            return it, "bank", it["id"]
    it = bank[now.toordinal() % len(bank)]
    return it, "bank", None  # reserve exhausted: recycle


def publish(item, key, origin, origin_id):
    """Render, host, publish to Instagram, mark done, log continuity. Returns permalink."""
    out_rel = f"posts/{key}"
    paths = render_post(item, HANDLE, os.path.join(ROOT, out_rel), NAME)
    rel = [os.path.relpath(p, ROOT) for p in paths]
    caption = build_caption(item)
    with open(os.path.join(ROOT, out_rel, "caption.txt"), "w") as fh:
        fh.write(caption)
    if DRY:
        log("DRY RUN rendered:", rel)
        print(caption)
        return ""
    me = api("GET", "me", fields="user_id,username")
    ig = me.get("user_id") or me.get("id")
    log("Posting as", me.get("username"), ig)

    def create_and_wait(rel_paths):
        sha = git_push(rel_paths + [f"{out_rel}/caption.txt"], f"Render post {key}")
        urls = public_urls(rel_paths, sha)
        if len(urls) == 1:
            cid = api("POST", f"{ig}/media", image_url=urls[0], caption=caption)["id"]
        else:
            kids = []
            for u in urls:
                kid = api("POST", f"{ig}/media", image_url=u, is_carousel_item="true")["id"]
                wait_ready(kid)
                kids.append(kid)
            cid = api("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
        wait_ready(cid)
        return cid

    try:
        cid = create_and_wait(rel)
    except SystemExit as e:
        # Full-phone (9:16) screenshots may be rejected as out of range; fall back to 4:5 once.
        if item.get("format") == "chat" and not item.get("height") and os.environ.get("CHAT_H") != "1350":
            log("Tall image rejected, retrying at 4:5:", e)
            os.environ["CHAT_H"] = "1350"
            paths = render_post(item, HANDLE, os.path.join(ROOT, out_rel), NAME)
            rel = [os.path.relpath(p, ROOT) for p in paths]
            cid = create_and_wait(rel)
        else:
            raise
    media_id = api("POST", f"{ig}/media_publish", creation_id=cid)["id"]
    link = api("GET", media_id, fields="permalink").get("permalink", "")
    log("Published", key, media_id, link)

    rec = {"key": key, "media_id": media_id, "permalink": link, "origin": origin,
           "posted_at": datetime.now(TZ).isoformat(), "pov": item.get("pov"), "bits": item.get("bits", []),
           "topic": item.get("topic"), "theme": item.get("theme"), "hour_pt": datetime.now(TZ).hour}
    rec[{"queue": "queue_id", "bank": "bank_id", "seed": "seed_id"}[origin]] = origin_id
    done_rel = f"posted/{key}.json"
    os.makedirs(os.path.join(ROOT, "posted"), exist_ok=True)
    with open(os.path.join(ROOT, done_rel), "w") as fh:
        json.dump(rec, fh, indent=2)
    canon = load("data/canon.json")
    canon["posted_log"].append({"key": key, "id": origin_id, "pov": item.get("pov"), "bits": item.get("bits", []),
                                "first_line": (item.get("messages") or [{}])[0].get("text", "")[:80]})
    with open(os.path.join(ROOT, "data/canon.json"), "w") as fh:
        json.dump(canon, fh, indent=1)
    git_push([done_rel, "data/canon.json"], f"Posted {key}: {link}")
    return link


def pick_slot():
    for slot, (start, end) in SLOTS.items():
        if os.path.exists(os.path.join(ROOT, "posted", f"{TODAY}-{slot}.json")):
            continue
        if FORCE or start <= now.hour <= end:
            return slot
    return None


def main():
    if not TOKEN and not DRY:
        raise SystemExit("IG_ACCESS_TOKEN secret is missing.")
    if SEED:
        items = load("data/seed.json")
        todo = [it for it in reversed(items) if not os.path.exists(os.path.join(ROOT, "posted", f"seed-{it['id']}.json"))]
        log(f"Seed mode: {len(todo)} posts to publish, {SEED_GAP}s apart")
        for n, it in enumerate(todo):
            publish(it, f"seed-{it['id']}", "seed", it["id"])
            if n < len(todo) - 1 and not DRY:
                time.sleep(SEED_GAP)
        return
    slot = pick_slot()
    if not slot:
        log(f"Nothing due at {now:%a %H:%M} PT (both windows done or outside windows).")
        return
    item, origin, oid = next_item()
    log("Slot", f"{TODAY}-{slot}", "using", origin, oid)
    publish(item, f"{TODAY}-{slot}", origin, oid)


if __name__ == "__main__":
    main()
