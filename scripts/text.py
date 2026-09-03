#!/usr/bin/env python3
"""Fetch a URL and print plain text, capped (default 2500 chars). Usage: text.py URL [chars]. Follows Google News redirects."""
import sys, re, html, urllib.request
url = sys.argv[1]; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
try:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=25) as r:
        final, raw = r.geturl(), r.read(1_500_000).decode("utf-8", "ignore")
    if "news.google.com" in final:
        m = re.search(r'data-n-au="([^"]+)"|href="(https?://[^"]+)"[^>]*rel="nofollow"', raw)
        if m:
            target = m.group(1) or m.group(2)
            req = urllib.request.Request(target, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                final, raw = r.geturl(), r.read(1_500_000).decode("utf-8", "ignore")
    raw = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
    print(f"URL: {final}\n{txt[:cap]}")
except Exception as e:
    print(f"FETCH FAILED ({type(e).__name__}: {str(e)[:100]})")
