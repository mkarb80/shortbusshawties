"""Shared helpers for the analytics/learning pipeline."""
import glob, json, os
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = ZoneInfo("America/Los_Angeles")
TOPICS = ["family", "dating", "money_work", "sleep_lazy", "dumb_decisions", "lateness", "festival",
          "marriage", "dessert", "marco_body", "wholesome_friends", "dark_life"]
BIT_TOPIC = {
    "family": "family", "parents": "family", "luis_family": "family",
    "dating": "dating", "marco_6pm": "dating",
    "broke_work": "money_work", "work": "money_work", "marco_money": "money_work", "marco_nojob": "money_work",
    "nate_sleepy": "sleep_lazy", "dre_lazy": "sleep_lazy", "nate_outsider": "sleep_lazy",
    "dumb_decision": "dumb_decisions", "bad_idea": "dumb_decisions", "dre_chaos": "dumb_decisions", "nate_sore_loser": "dumb_decisions",
    "benny_eta": "lateness", "luis_festival": "festival",
    "dre_weird": "marriage", "dre_wife_accepted": "marriage",
    "nate_dessert": "dessert", "marco_back": "marco_body", "marco_butt": "marco_body",
    "benny_positive": "wholesome_friends", "benny_social": "wholesome_friends", "plans": "wholesome_friends",
}

def load(path, default=None):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return default
    with open(p) as fh:
        return json.load(fh)

def save(path, obj):
    p = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)

def topic_of(item):
    if item.get("topic") in TOPICS:
        return item["topic"]
    for b in item.get("bits", []):
        if b in BIT_TOPIC:
            return BIT_TOPIC[b]
    return "other"

def all_items():
    """Every known post definition by (origin, id)."""
    out = {}
    for f in glob.glob(os.path.join(ROOT, "queue", "*.json")):
        it = json.load(open(f)); out[("queue", os.path.splitext(os.path.basename(f))[0])] = it
    for it in load("data/seed.json", []):
        out[("seed", it["id"])] = it
    for it in load("data/bank.json", []):
        out[("bank", it["id"])] = it
    for f in glob.glob(os.path.join(ROOT, "data", "retired", "*.json")):
        it = json.load(open(f)); out[("queue", os.path.splitext(os.path.basename(f))[0])] = it
    return out

def schedule():
    s = load("data/schedule.json", {}) or {}
    return {"a": tuple(s.get("a", (12, 14))), "b": tuple(s.get("b", (20, 22)))}

def unposted_queue():
    done = set()
    for f in glob.glob(os.path.join(ROOT, "posted", "*.json")):
        v = json.load(open(f)).get("queue_id")
        if v: done.add(v)
    ids = [os.path.splitext(os.path.basename(f))[0] for f in sorted(glob.glob(os.path.join(ROOT, "queue", "*.json")))]
    return [i for i in ids if i not in done]
