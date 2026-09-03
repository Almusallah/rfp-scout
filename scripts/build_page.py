#!/usr/bin/env python3
"""Rebuild docs/index.html from state.json + runs/last_run.json. No dependencies."""
import json, os, html
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
state = json.load(open(P("state.json")))
lr = json.load(open(P("runs", "last_run.json"))) if os.path.exists(P("runs", "last_run.json")) else {}
E = html.escape
today = date.today().isoformat()
def row(i):
    dl = i.get("deadline") or "—"
    late = i.get("deadline") and i["deadline"] < today
    return (f'<article class="c {i["verdict"]}{" late" if late else ""}"><h3><a href="{E(i["url"])}" target="_blank" rel="noopener">{E(i["title"])}</a></h3>'
            f'<p class="m"><b>{E(i.get("issuer") or "")}</b> {E(i.get("country") or "")} · deadline <b>{E(dl)}</b> · seen {i["first_seen"]} · <span class="s">{E(i["source"])}</span></p>'
            f'<p>{E(i.get("scope") or "")}</p><p class="w">{E(i.get("why") or "")}{(" · " + E(i["eligibility"])) if i.get("eligibility") else ""}</p></article>')
fits = sorted([i for i in state["items"] if i["verdict"] == "fit"], key=lambda i: (i.get("deadline") or "9999", -i["score"]))
watch = sorted([i for i in state["items"] if i["verdict"] == "watch"], key=lambda i: i["first_seen"], reverse=True)[:40]
rej = [i for i in state["items"] if i["verdict"] == "reject"]
health = "".join(f'<li class="{"ok" if s["ok"] else ("opt" if s.get("optional") else "bad")}">{E(s["id"])}: {"ok, " + str(s.get("items",0)) + " items, " + str(s.get("new",0)) + " new" if s["ok"] else E(s.get("error",""))}</li>' for s in lr.get("sources", []))
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RFP Scout — art production & cultural project tenders</title>
<style>:root{{--ink:#181314;--bg:#f7f5f2;--fit:#0a7a3d;--watch:#a86b00;--mute:#6b6b6b}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Helvetica,Arial,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:24px 16px 80px}}h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:16px;margin:32px 0 8px;text-transform:uppercase;letter-spacing:.06em}}
.c{{border-left:4px solid #ccc;background:#fff;padding:10px 14px;margin:10px 0;border-radius:4px}}.c.fit{{border-color:var(--fit)}}.c.watch{{border-color:var(--watch)}}.c.late{{opacity:.55}}
h3{{font-size:16px;margin:0 0 4px}}a{{color:var(--ink)}}.m,.w{{color:var(--mute);font-size:13px;margin:2px 0}}.s{{font-family:monospace}}p{{margin:4px 0}}
details{{margin-top:8px}}li.ok{{color:var(--fit)}}li.bad{{color:#b00020}}li.opt{{color:var(--mute)}}ul{{font-size:12px;font-family:monospace;padding-left:18px}}</style></head><body><main>
<h1>RFP Scout</h1><p class="m">Tenders and calls in art production, exhibition and cultural project management that a Vietnam-registered LTD could answer. Asia / SEA first, plus Gulf and Central Asia publishers. Twice a week, automated, observe-only. Last run: <b>{E(lr.get("ran_at","—"))}</b> · {len(fits)} fit · {len(watch)} watch · {len(rej)} rejected.</p>
<h2>Fit — act on these</h2>{"".join(row(i) for i in fits) or "<p class='m'>Nothing fitting yet.</p>"}
<h2>Watch — unclear or early</h2>{"".join(row(i) for i in watch) or "<p class='m'>—</p>"}
<details><summary>Rejected ({len(rej)}) and source health</summary><ul>{"".join(f"<li>{E(i['title'])} — {E(i.get('why',''))}</li>" for i in rej[-60:])}</ul><h2>Sources</h2><ul>{health}</ul></details>
<p class="m" style="margin-top:40px">Repo: <a href="https://github.com/Almusallah/rfp-scout">Almusallah/rfp-scout</a>. Edit <code>sources.json</code> to add a portal, <code>PROFILE.md</code> to change what counts as a fit.</p>
</main></body></html>"""
os.makedirs(P("docs"), exist_ok=True)
open(P("docs", "index.html"), "w").write(page)
print(f"page: {len(fits)} fit, {len(watch)} watch, {len(rej)} rejected")
