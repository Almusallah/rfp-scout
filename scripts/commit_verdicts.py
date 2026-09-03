#!/usr/bin/env python3
"""Merge runs/verdicts.json (written by the agent) into state.json. Every candidate in runs/new_candidates.json
is marked seen, whether or not it got a verdict. Prunes 'reject' items older than 120 days from items[] (seen[] is kept)."""
import json, os
from datetime import datetime, timezone, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
state = json.load(open(P("state.json"))) if os.path.exists(P("state.json")) else {"items": [], "seen": {}}
cands = {c["id"]: c for c in json.load(open(P("runs", "new_candidates.json")))} if os.path.exists(P("runs", "new_candidates.json")) else {}
verdicts = json.load(open(P("runs", "verdicts.json"))) if os.path.exists(P("runs", "verdicts.json")) else []
today = datetime.now(timezone.utc).date().isoformat()
byid = {v["id"]: v for v in verdicts if "id" in v}
added = {"fit": 0, "watch": 0, "reject": 0}
for cid, c in cands.items():
    v = byid.get(cid, {})
    verdict = v.get("verdict", "reject")
    if verdict not in added: verdict = "reject"
    item = {"id": cid, "title": v.get("title") or c["title"], "url": v.get("url") or c["url"], "source": c["source"], "score": c["score"],
            "verdict": verdict, "issuer": v.get("issuer", ""), "country": v.get("country", ""), "deadline": v.get("deadline", ""),
            "scope": v.get("scope", ""), "eligibility": v.get("eligibility", ""), "why": v.get("why", ""), "first_seen": today}
    state["items"].append(item); added[verdict] += 1
    state["seen"][c["key"]] = {"t": cid, "d": today}
    state["seen"][cid] = {"t": cid, "d": today}
cutoff = (datetime.now(timezone.utc) - timedelta(days=120)).date().isoformat()
state["items"] = [i for i in state["items"] if not (i["verdict"] == "reject" and i["first_seen"] < cutoff)]
state["last_run"] = {"date": today, "added": added}
json.dump(state, open(P("state.json"), "w"), indent=1, ensure_ascii=False)
if os.path.exists(P("runs", "verdicts.json")): os.remove(P("runs", "verdicts.json"))
print(f"state: +{added['fit']} fit, +{added['watch']} watch, +{added['reject']} reject; {len(state['items'])} items, {len(state['seen'])} seen keys")
