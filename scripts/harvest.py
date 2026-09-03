#!/usr/bin/env python3
"""Server-side harvester. Stdlib only. Fetches every source in sources.json, extracts items,
keyword-filters them, drops anything already in state.json, and writes runs/new_candidates.json.
Never raises on a single source; source health goes to runs/last_run.json. Exit 0 always."""
import json, re, sys, os, time, hashlib, html, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = json.load(open(os.path.join(ROOT, "sources.json")))["sources"]
STATE_P = os.path.join(ROOT, "state.json")
STATE = json.load(open(STATE_P)) if os.path.exists(STATE_P) else {"items": [], "seen": {}}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "40"))

SIG_CALL = re.compile(r"\b(rfp|rfq|rfi|itb|eoi|request for proposals?|request for quotations?|request for information|call for proposals?|call for tenders?|call for applications?|call for submissions?|call for entries|call for expressions? of interest|expressions? of interest|invitation to (bid|tender)|tender|tendering|procurement|open call|seeking proposals|bid(s|ding)? (invited|open)|solicitation)\b", re.I)
SIG_DOMAIN = re.compile(r"\b(exhibitions?|museums?|biennales?|biennials?|triennales?|triennials?|pavilions?|galler(y|ies)|curators?|curatorial|art(work|works|ist|ists|s)?|cultural|culture|festival|installation|scenograph(y|ic)|heritage|design week|creative|public art|art production|exhibition (design|production|fabrication|build)|art handling|visual arts|performing arts|arts centre|arts center)\b", re.I)
NEG = re.compile(r"\b(job|jobs|hiring|vacanc(y|ies)|salary|internship|scholarship|phd|postdoc|webinar|paper(s)? (call|submission)|conference paper|abstract submission|call for papers|academic)\b", re.I)
GEO = re.compile(r"\b(vietnam|viet nam|hanoi|ho chi minh|saigon|da nang|thailand|bangkok|chiang mai|singapore|malaysia|kuala lumpur|penang|indonesia|jakarta|bali|philippines|manila|cambodia|phnom penh|laos|myanmar|brunei|asean|south-?east asia|japan|tokyo|osaka|kyoto|korea|seoul|busan|hong kong|macau|taiwan|taipei|china|shanghai|beijing|shenzhen|india|delhi|mumbai|sri lanka|uzbekistan|tashkent|bukhara|samarkand|kazakhstan|almaty|astana|central asia|mekong|greater mekong|saudi|riyadh|jeddah|diriyah|alula|qatar|doha|uae|dubai|abu dhabi|sharjah|oman|muscat|bahrain|kuwait|gulf|gcc|asia)\b", re.I)

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(2_000_000).decode("utf-8", "ignore")

def norm_url(u):
    u = u.strip()
    p = urllib.parse.urlsplit(u)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))]
    return urllib.parse.urlunsplit((p.scheme.lower() or "https", p.netloc.lower(), p.path.rstrip("/"), urllib.parse.urlencode(q), ""))

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def title_key(t):
    return hashlib.sha1(re.sub(r"[^a-z0-9]+", "", t.lower())[:80].encode()).hexdigest()[:16]

def parse_rss(txt):
    items = []
    try:
        root = ET.fromstring(txt.encode("utf-8", "ignore"))
    except ET.ParseError:
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for it in root.iter("item"):
        items.append({"title": clean(it.findtext("title")), "url": (it.findtext("link") or "").strip(),
                      "summary": clean(it.findtext("description"))[:400], "published": (it.findtext("pubDate") or "").strip(),
                      "publisher": clean((it.find("source").text if it.find("source") is not None else ""))})
    for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
        link = it.find("atom:link", ns)
        items.append({"title": clean(it.findtext("atom:title", default="", namespaces=ns)), "url": (link.get("href") if link is not None else "").strip(),
                      "summary": clean(it.findtext("atom:summary", default="", namespaces=ns))[:400], "published": it.findtext("atom:updated", default="", namespaces=ns), "publisher": ""})
    return items

def parse_html(txt, base, must=None):
    items, seen = [], set()
    rx = re.compile(must, re.I) if must else None
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', txt, re.I | re.S):
        href, text = m.group(1), clean(m.group(2))
        if not (15 <= len(text) <= 220): continue
        url = urllib.parse.urljoin(base, href)
        if not url.startswith("http"): continue
        if rx and not rx.search(url): continue
        k = norm_url(url)
        if k in seen: continue
        seen.add(k)
        items.append({"title": text, "url": url, "summary": "", "published": "", "publisher": urllib.parse.urlsplit(base).netloc})
    return items

def score(item, mode, require_geo=False):
    text = f"{item['title']} {item['summary']}"
    if require_geo and not GEO.search(text): return 0
    has_call, has_dom = bool(SIG_CALL.search(text)), bool(SIG_DOMAIN.search(text))
    if mode == "tenderpage":
        if not has_dom: return 0
    elif not (has_call and has_dom):
        return 0
    if NEG.search(text) and not has_call: return 0
    s = 3 * len(set(m.group(0).lower() for m in SIG_DOMAIN.finditer(text)))
    s += 4 * len(set(m.group(0).lower() for m in GEO.finditer(text)))
    s += 3 if has_call else 0
    s -= 5 if NEG.search(text) else 0
    for w in ("production", "project management", "exhibition design", "fabrication", "scenograph", "installation", "art handling", "biennale", "biennial", "pavilion"):
        if w in text.lower(): s += 3
    return max(s, 0)

seen_urls = set(STATE.get("seen", {}).keys())
seen_titles = set(v.get("t", "") for v in STATE.get("seen", {}).values())
health, cands, dedup = [], [], set()
for src in SRC:
    t0 = time.time()
    try:
        txt = fetch(src["url"])
        items = parse_rss(txt) if src["type"] == "rss" else parse_html(txt, src["url"], src.get("link_must_match"))
        kept = 0
        for it in items:
            if not it["url"] or not it["title"]: continue
            k, tk = norm_url(it["url"]), title_key(it["title"])
            if k in seen_urls or tk in seen_titles or k in dedup or tk in dedup: continue
            sc = score(it, src.get("mode", ""), src.get("require_geo", False))
            if sc <= 0: continue
            dedup.add(k); dedup.add(tk)
            it.update({"id": tk, "key": k, "source": src["id"], "score": sc})
            cands.append(it); kept += 1
        health.append({"id": src["id"], "ok": True, "items": len(items), "new": kept, "secs": round(time.time() - t0, 1)})
    except Exception as e:
        health.append({"id": src["id"], "ok": False, "optional": src.get("optional", False), "error": f"{type(e).__name__}: {str(e)[:120]}"})

cands.sort(key=lambda x: -x["score"])
overflow = cands[MAX_CANDIDATES:]
cands = cands[:MAX_CANDIDATES]
os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
json.dump(cands, open(os.path.join(ROOT, "runs", "new_candidates.json"), "w"), indent=1, ensure_ascii=False)
json.dump({"ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "candidates": len(cands), "overflow_dropped": len(overflow), "sources": health},
          open(os.path.join(ROOT, "runs", "last_run.json"), "w"), indent=1)
bad = [h for h in health if not h["ok"] and not h.get("optional")]
print(f"harvest: {len(cands)} new candidates (dropped {len(overflow)} low-score overflow); {len(health)-len([h for h in health if not h['ok']])}/{len(health)} sources ok"
      + (f"; NON-OPTIONAL FAILURES: {[h['id'] for h in bad]}" if bad else ""))
