"""Daily 10am PT job: analyze performance, update strategy, refill the queue to 10 days, post a readout.

Steps: analyze.py -> decide (topic mix, best posting hours) -> write data/schedule.json ->
generate posts with the Claude API until 20 are queued (10 days x 2/day) -> data/learnings.md (<=10 lines)
-> GitHub issue with the same text (GitHub emails the repo owner).

Env: IG_ACCESS_TOKEN, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, GITHUB_TOKEN, GITHUB_REPOSITORY,
     FORCE=1 (ignore the 10am gate), MOCK_LLM=<json file> (offline test), DRY_RUN=1 (write nothing remote), TARGET (default 20).
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.error, glob
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, TZ, TOPICS, load, save, topic_of, unposted_queue, schedule, all_items
from render_humor import render_post, chat

NOW = datetime.now(TZ)
TODAY = NOW.strftime("%Y-%m-%d")
TARGET = int(os.environ.get("TARGET") or 20)
FORCE = os.environ.get("FORCE") == "1"
DRY = os.environ.get("DRY_RUN") == "1"
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODELS = [m for m in [os.environ.get("ANTHROPIC_MODEL"), "claude-sonnet-5-5", "claude-sonnet-4-5"] if m]
CAST = ["Dre", "Nate", "Marco", "Benny", "Luis"]
BANNED = re.compile(r"\b(n[i1]gg|f[a4]gg?|retard|tranny|kike|sp[i1]c|chink|gook|wetback|dyke|coon)\w*|kill (my|him|her)self|\bkys\b|suicid|\brape\b|\bcape\b|seattle", re.I)


def log(*a): print(f"[{datetime.now(TZ):%H:%M:%S}]", *a, flush=True)


def sh(*cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------- LLM
def claude(system, user, max_tokens=8000):
    mock = os.environ.get("MOCK_LLM")
    if mock:
        return open(mock).read()
    if not KEY:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    last = None
    for model in MODELS:
        for attempt in range(3):
            body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system,
                               "messages": [{"role": "user", "content": user}]}).encode()
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                         headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return "".join(b.get("text", "") for b in json.load(r)["content"])
            except urllib.error.HTTPError as e:
                last = f"{model}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}"
                if e.code in (404, 400):
                    break  # try the next model name
                time.sleep(8 * (attempt + 1))
            except Exception as e:
                last = f"{model}: {e}"; time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"Claude API failed: {last}")


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


# ---------------------------------------------------------------- strategy
def decide(stats):
    mature = stats.get("posts_mature", 0)
    by_topic = stats.get("by_topic", {})
    proven = sorted([(k, v) for k, v in by_topic.items() if v["n"] >= 2 and k in TOPICS], key=lambda kv: -kv[1]["shrunk"])
    top = [k for k, _ in proven[:3]]
    weak = [k for k, v in sorted(proven, key=lambda kv: kv[1]["shrunk"])[:2] if len(proven) > 3]
    seen = {k for k, v in by_topic.items() if v["n"] >= 1}
    explore = [t for t in TOPICS if t not in seen] or [t for t in TOPICS if t not in top]
    plan = {"double_down": top, "avoid_more_of": weak, "explore": explore[:4], "mature_posts": mature}
    # posting hours: only move once there's evidence (>=8 mature posts and the candidate hour has >=2 samples)
    sched = schedule(); changes = []
    by_hour = {int(k): v for k, v in stats.get("by_hour", {}).items()}
    if mature >= 8:
        for slot, (lo, hi, cap) in {"a": (8, 15, 17), "b": (17, 22, 23)}.items():
            cands = {h: v for h, v in by_hour.items() if lo <= h <= hi and v["n"] >= 2}
            if cands:
                best = max(cands, key=lambda h: cands[h]["shrunk"])
                new = (best, min(best + 2, cap))
                if new != tuple(sched[slot]):
                    changes.append(f"slot {slot}: {sched[slot][0]}:00 -> {new[0]}:00 PT (best hour {best}:00, n={cands[best]['n']})")
                    sched[slot] = new
    return plan, sched, changes


# ---------------------------------------------------------------- generation
def style_guide():
    chars = open(os.path.join(ROOT, "data", "characters.md")).read()
    gold = [load(f"queue/a{i:02d}.json") for i in range(1, 11)]
    gold = [g for g in gold if g]
    ex = json.dumps([{k: g[k] for k in ("pov", "theme", "time", "topic", "messages", "caption") if k in g} for g in gold[:6]], ensure_ascii=False)
    return f"""You write posts for the Instagram page @shortbusshawties: screenshots of a group text between five friends in their 30s called "Short Bus Shawties".

CHARACTER BIBLE:
{chars}

THE VOICE THE OWNER WANTS (this overrides anything above that feels staged):
- Dry, flat, realistic. Real people texting, not characters performing bits. The funny comes from specific, mundane, slightly sad details and understatement, usually a flat last line.
- Do NOT announce running bits or use catchphrases ("she has accepted it", "update:" openers, "marco in seattle", etc.). Traits (Benny late, Nate sleepy, Marco's back, Luis's hedged long texts) show up through what people do, never named as a bit.
- Messages are short, lowercase, fragments, people send several short bubbles in a row, ignore each other, answer sideways. No exclamation spam (only Benny, sparingly). No jokes that explain themselves.
- Dark but light-hearted: money, family, dating, work, laziness, aging bodies, dumb decisions. Aim at life and the guys' own stupidity. NEVER slurs, never a punchline about race, religion, disability, sexuality or body type, no sexual content, nothing about self-harm, no real people, no named wives/girlfriends (refer to "my wife", "my mom", etc.).
- Everyone texts remotely from their own place. One sender is the POV (blue bubble on the right); not every guy appears in every post.
- Banned premises (owner disliked): a cape; "marco in seattle"; "scared of my wife and jealous".

GOOD EXAMPLES (the style to match):
{ex}

OUTPUT: strict JSON only, no prose: {{"posts":[{{"pov":"Marco","theme":"light|dark","time":"Tue 4:15 PM","topic":"<one of {TOPICS}>","bits":["tag"],"messages":[{{"from":"Dre","text":"..."}}],"caption":"short lowercase caption\\n\\n#groupchat #tag #tag #tag #tag"}}]}}
Rules: 4-9 messages, each text under 130 characters (Luis may reach 170), at most 5 hashtags, theme alternates light/dark, POV varies, times look natural (a weekday + time)."""


def valid(p, recent_first):
    try:
        if p.get("pov") not in CAST or p.get("theme") not in ("light", "dark"): return "pov/theme"
        ms = p["messages"]
        if not 4 <= len(ms) <= 9: return "length"
        for m in ms:
            if m.get("from") not in CAST or not isinstance(m.get("text"), str) or not m["text"].strip(): return "msg"
            if len(m["text"]) > 175: return "long"
        if p["pov"] not in {m["from"] for m in ms}: return "pov absent"
        if len(re.findall(r"#\w+", p.get("caption", ""))) > 5: return "hashtags"
        blob = " ".join(m["text"] for m in ms) + " " + p.get("caption", "")
        if BANNED.search(blob): return "banned"
        if ms[0]["text"].strip().lower()[:40] in recent_first: return "duplicate"
        if p.get("topic") not in TOPICS: p["topic"] = topic_of(p)
        return None
    except Exception as e:
        return f"error {e}"


def recent_lines():
    out = set()
    for it in all_items().values():
        if it.get("messages"):
            out.add(it["messages"][0]["text"].strip().lower()[:40])
    for e in (load("data/canon.json", {}) or {}).get("posted_log", []):
        out.add((e.get("first_line") or "").strip().lower()[:40])
    return out


def generate(need, plan, stats):
    made, tried, batches = [], 0, 0
    recent = recent_lines()
    while len(made) < need and batches < 6:
        batches += 1
        n = min(10, need - len(made) + 2)
        top_posts = [{"topic": t["topic"], "first_line": t["first_line"], "score": t["score"]} for t in stats.get("top", [])[:3]]
        user = (f"Write {n} NEW posts. Topic plan: roughly 60% from double_down topics {plan['double_down'] or 'any (no data yet, spread evenly)'}, "
                f"25% from explore topics {plan['explore']}, rest anything. Avoid more of: {plan['avoid_more_of'] or 'nothing yet'}. "
                f"Our best performing posts so far (write NEW situations with the same mechanism or subject, never copies): {json.dumps(top_posts)}. "
                f"Do not reuse any of these opening lines: {sorted(recent)[:80]}")
        try:
            data = parse_json(claude(style_guide(), user))
        except Exception as e:
            log("generation failed:", e); break
        for p in data.get("posts", []):
            why = valid(p, recent)
            if why:
                log("rejected:", why, (p.get("messages") or [{}])[0].get("text", "")[:40]); continue
            try:
                render_post({**p, "id": "check", "format": "chat"}, "@shortbusshawties", "/tmp/check")
                if chat.last_size < 34:
                    log("rejected: too crowded to read"); continue
            except Exception as e:
                log("rejected: render failed", e); continue
            recent.add(p["messages"][0]["text"].strip().lower()[:40]); made.append(p)
            if len(made) >= need: break
    return made


def write_queue(posts):
    names = []
    for i, p in enumerate(posts, 1):
        qid = f"g{NOW:%Y%m%d}-{i:02d}"
        item = {"id": qid, "format": "chat", **{k: p[k] for k in ("pov", "theme", "time", "topic", "bits", "messages", "caption") if k in p}}
        item.setdefault("bits", [])
        save(f"queue/{qid}.json", item); names.append(qid)
    return names


# ---------------------------------------------------------------- readout
def readout(stats, plan, changes, added, queue_len, note):
    lines = []
    if stats.get("posts_mature", 0) == 0:
        lines.append(f"No post is 24h old with data yet ({stats.get('posts_total', 0)} live), so nothing is changing today.")
    else:
        lines.append(f"{stats['posts_mature']} posts measured. Score = shares/saves/comments/likes per 100 reached"
                     f"{'' if stats.get('reach_insights') else ' (reach unavailable: likes+comments only)'}.")
        bt = sorted(stats.get("by_topic", {}).items(), key=lambda kv: -kv[1]["shrunk"])
        if bt: lines.append("Best subjects: " + ", ".join(f"{k} ({v['mean']}, n={v['n']})" for k, v in bt[:3]) + ".")
        if len(bt) > 3: lines.append("Weakest: " + ", ".join(f"{k} ({v['mean']})" for k, v in bt[-2:]) + ".")
        bp = sorted(stats.get("by_pov", {}).items(), key=lambda kv: -kv[1]["shrunk"])
        if bp: lines.append("Best POV character: " + ", ".join(f"{k} ({v['mean']})" for k, v in bp[:2]) + ".")
        bh = sorted(stats.get("by_hour", {}).items(), key=lambda kv: -kv[1]["shrunk"])
        if bh: lines.append("Best posting hours (PT): " + ", ".join(f"{k}:00 ({v['mean']}, n={v['n']})" for k, v in bh[:2]) + ".")
        th = stats.get("by_theme", {})
        if len(th) == 2: lines.append("Light vs dark: " + ", ".join(f"{k} {v['mean']}" for k, v in th.items()) + ".")
        top = (stats.get("top") or [None])[0]
        if top: lines.append(f"Top post: \"{top['first_line']}\" ({top['topic']}, score {top['score']}).")
    lines.append("Pivot: " + (f"doubling down on {', '.join(plan['double_down'])}; exploring {', '.join(plan['explore'][:2])}." if plan["double_down"]
                              else f"not enough proof yet, spreading across topics and testing {', '.join(plan['explore'][:3])}."))
    lines.append("Schedule: " + ("; ".join(changes) if changes else "posting windows unchanged (need more data)."))
    lines.append(note or f"Queue: +{added} new posts, {queue_len} ready (~{queue_len // 2} days).")
    return lines[:10]


def open_issue(title, body):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (tok and repo) or DRY:
        return
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues", method="POST",
                                 data=json.dumps({"title": title, "body": body}).encode(),
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        log("issue failed:", e)


def git_push(msg):
    sh("git", "config", "user.name", "shortbus-bot"); sh("git", "config", "user.email", "shortbus-bot@users.noreply.github.com")
    sh("git", "add", "-A", "data", "queue")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    sh("git", "commit", "-m", msg)
    for i in range(4):
        try:
            sh("git", "pull", "--rebase", "-q"); sh("git", "push", "-q"); return
        except subprocess.CalledProcessError as e:
            log("push retry", e.stderr); time.sleep(5)
    raise SystemExit("push failed")


def main():
    state = load("data/learn_state.json", {}) or {}
    if not FORCE and (NOW.hour != 10 or state.get("last_run") == TODAY):
        log(f"Not the 10am run (PT hour {NOW.hour}, last run {state.get('last_run')})."); return
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "analyze.py")], check=False)
    stats = load("data/stats.json", {}) or {}
    plan, sched, changes = decide(stats)
    save("data/schedule.json", {"a": list(sched["a"]), "b": list(sched["b"]), "updated": TODAY})
    queue = unposted_queue(); need = max(0, TARGET - len(queue)); added, note = 0, None
    if need:
        try:
            posts = generate(need, plan, stats)
            added = len(write_queue(posts))
            if added < need: note = f"Queue: only +{added} of {need} needed posts passed checks; {len(queue) + added} ready (~{(len(queue) + added) // 2} days)."
        except Exception as e:
            note = f"Queue NOT refilled ({e}). {len(queue)} posts ready (~{len(queue) // 2} days)."
    lines = readout(stats, plan, changes, added, len(unposted_queue()), note)
    text = "\n".join(lines)
    with open(os.path.join(ROOT, "data", "learnings.md"), "w") as fh:
        fh.write(f"# Learnings {TODAY}\n\n" + text + "\n")
    with open(os.path.join(ROOT, "data", "learnings_log.md"), "a") as fh:
        fh.write(f"\n## {TODAY}\n{text}\n")
    save("data/strategy.json", {"updated": TODAY, **plan})
    save("data/learn_state.json", {"last_run": TODAY})
    print("\n" + text)
    if not DRY:
        git_push(f"Daily learn {TODAY}: +{added} posts")
        open_issue(f"Daily learnings {TODAY}", text)


if __name__ == "__main__":
    main()
