"""Check the queue after writing new posts: moves any post that breaks the rules to data/rejected/ and refreshes data/state.json.
Run from the repo root:  python scripts/validate_queue.py   (needs: pip install pillow)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import learn

if __name__ == "__main__":
    moved = learn.sweep()
    learn.write_state(moved)
    for qid, why in moved:
        print(f"REJECTED {qid}: {why}")
    import json
    s = json.load(open(os.path.join(learn.ROOT, "data", "state.json")))
    print(f"queue: {s['unposted_count']} ready, need {s['need']} more to reach {s['target']}")
