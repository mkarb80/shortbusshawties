"""Pull performance for every published post and aggregate by topic, character, theme and time.

Writes data/insights.json (per post) and data/stats.json (aggregates).
Score = weighted engagement per 100 accounts reached (shares x5, saves x4, comments x3, likes x1).
If the token lacks the insights permission, falls back to likes + comments only (relative, not per-reach).
"""
import glob, json, os, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from statistics import mean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, TZ, load, save, topic_of, all_items

API = "https://graph.instagram.com"
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
MIN_AGE_H = 24
W = {"shares": 5, "saved": 4, "comments": 3, "likes": 1}


def get(path, **p):
    p["access_token"] = TOKEN
    try:
        with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(errors="replace").replace(TOKEN, "***")[:300]}


def media_list():
    out, url = [], None
    r = get("me/media", fields="id,timestamp,like_count,comments_count,permalink,media_type", limit=100)
    while True:
        if "error" in r:
            print("media list error:", r["error"]); return out
        out += r.get("data", [])
        nxt = r.get("paging", {}).get("next")
        if not nxt:
            return out
        try:
            with urllib.request.urlopen(nxt, timeout=60) as resp: r = json.load(resp)
        except Exception as e:
            print("paging stopped:", e); return out


def insights(mid):
    r = get(f"{mid}/insights", metric="reach,saved,shares,total_interactions")
    if "error" in r:
        return None
    return {d["name"]: (d["values"][0]["value"] if d.get("values") else d.get("total_value", {}).get("value", 0)) for d in r.get("data", [])}


def main():
    posted = {}
    for f in glob.glob(os.path.join(ROOT, "posted", "*.json")):
        rec = json.load(open(f)); posted[rec.get("media_id")] = rec
    items = all_items()
    rows, have_insights = [], True
    live = media_list() if TOKEN else []
    if not TOKEN:
        print("No IG token: analysis skipped (no live data).")
    now = datetime.now(timezone.utc)
    for m in live:
        rec = posted.get(m["id"])
        if not rec:
            continue  # not posted by the bot
        origin = rec.get("origin"); oid = rec.get("queue_id") or rec.get("bank_id") or rec.get("seed_id")
        it = items.get((origin, oid), {})
        ts = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        age_h = (now - ts).total_seconds() / 3600
        ins = insights(m["id"]) if have_insights else None
        if ins is None:
            have_insights = False
        likes, com = m.get("like_count", 0) or 0, m.get("comments_count", 0) or 0
        if ins:
            eng = likes * W["likes"] + com * W["comments"] + (ins.get("saved", 0) * W["saved"]) + (ins.get("shares", 0) * W["shares"])
            score = eng / max(ins.get("reach", 0), 50) * 100
        else:
            eng = likes * W["likes"] + com * W["comments"]; score = float(eng)
        local = ts.astimezone(TZ)
        rows.append({"media_id": m["id"], "key": rec["key"], "permalink": m.get("permalink"), "age_h": round(age_h, 1),
                     "mature": age_h >= MIN_AGE_H, "likes": likes, "comments": com, **(ins or {}),
                     "score": round(score, 3), "topic": topic_of(it), "pov": it.get("pov") or rec.get("pov"),
                     "theme": it.get("theme"), "hour_pt": local.hour, "dow": local.strftime("%a"),
                     "origin": origin, "first_line": (it.get("messages") or [{}])[0].get("text", "")[:70]})
    save("data/insights.json", {"updated": now.isoformat(), "have_reach_insights": bool(rows) and have_insights, "posts": rows})

    mature = [r for r in rows if r["mature"]]
    gmean = mean([r["score"] for r in mature]) if mature else 0

    def agg(keyf):
        g = {}
        for r in mature:
            g.setdefault(keyf(r), []).append(r["score"])
        # shrink toward the global mean so one lucky post can't dominate (prior weight = 2 posts)
        return {k: {"n": len(v), "mean": round(mean(v), 3), "shrunk": round((sum(v) + 2 * gmean) / (len(v) + 2), 3)} for k, v in g.items() if k}
    stats = {"updated": now.isoformat(), "posts_total": len(rows), "posts_mature": len(mature), "global_mean": round(gmean, 3),
             "reach_insights": bool(rows) and have_insights,
             "by_topic": agg(lambda r: r["topic"]), "by_pov": agg(lambda r: r["pov"]), "by_theme": agg(lambda r: r["theme"]),
             "by_hour": agg(lambda r: r["hour_pt"]), "by_dow": agg(lambda r: r["dow"]),
             "top": sorted(mature, key=lambda r: -r["score"])[:5], "bottom": sorted(mature, key=lambda r: r["score"])[:5]}
    save("data/stats.json", stats)
    print(f"analyzed {len(rows)} posts ({len(mature)} mature), reach insights: {stats['reach_insights']}")


if __name__ == "__main__":
    main()
