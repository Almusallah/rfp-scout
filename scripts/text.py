#!/usr/bin/env python3
"""Fetch a URL and print plain text, capped (default 2500 chars). Usage: text.py URL [chars].
Google News RSS links (news.google.com/rss/articles/<id>) are decoded to the real article URL first
(batchexecute 'garturlreq' method), so the reader sees the notice, not the Google stub."""
import sys, re, json, html, urllib.request, urllib.parse
url = sys.argv[1]; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

def get(u, data=None, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept-Language": "en"}; h.update(headers or {})
    req = urllib.request.Request(u, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.geturl(), r.read(1_500_000).decode("utf-8", "ignore")

def decode_gnews(u):
    m = re.search(r"news\.google\.com/(?:rss/)?articles/([^?/]+)", u)
    if not m: return u
    art = m.group(1)
    try:
        _, page = get(f"https://news.google.com/articles/{art}")
        sg = re.search(r'data-n-a-sg="([^"]+)"', page); ts = re.search(r'data-n-a-ts="([^"]+)"', page)
        if not (sg and ts): return u
        payload = ["Fbv4je", f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{art}",{ts.group(1)},"{sg.group(1)}"]']
        body = "f.req=" + urllib.parse.quote(json.dumps([[payload]]))
        _, resp = get("https://news.google.com/_/DotsSplashUi/data/batchexecute", data=body.encode(), headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        chunk = resp.split("\n\n")[1]
        parsed = json.loads(chunk)
        real = json.loads(parsed[0][2])[1]
        return real if isinstance(real, str) and real.startswith("http") else u
    except Exception:
        return u

try:
    target = decode_gnews(url)
    final, raw = get(target)
    raw = re.sub(r"<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
    if re.search(r"testing whether you are a human|verify you are human|enable javascript and cookies|access denied|attention required", txt[:600], re.I) or len(txt) < 200:
        print(f"URL: {final}\nBLOCKED_OR_EMPTY: page is a bot-check or has no text; use the candidate's title+summary and this URL, do not guess details.")
    else:
        print(f"URL: {final}\n{txt[:cap]}")
except Exception as e:
    print(f"FETCH FAILED ({type(e).__name__}: {str(e)[:100]}) for {target if 'target' in dir() else url}")
