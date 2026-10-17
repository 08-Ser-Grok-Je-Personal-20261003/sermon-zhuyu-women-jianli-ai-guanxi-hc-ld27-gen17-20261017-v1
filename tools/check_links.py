#!/usr/bin/env python3
"""Check every internal link / anchor / asset reference in the built pages (relative links only)."""
import re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, unquote

ROOT = Path(__file__).resolve().parent.parent


class L(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.assets = set(), [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.add(a["id"])
        if tag == "a" and a.get("name"): self.ids.add(a["name"])
        if tag == "a" and "href" in a: self.links.append(a["href"])
        if tag in ("script", "img") and "src" in a: self.assets.append(a["src"])
        if tag == "link" and "href" in a: self.assets.append(a["href"])


pages = {p.name: p for p in sorted(ROOT.glob("*.html"))}
info = {}
for n, p in pages.items():
    l = L(); l.feed(p.read_text("utf-8")); info[n] = l
bad = 0; total = 0; ext = 0
for n, l in info.items():
    for href in l.links + l.assets:
        if re.match(r"^(https?:|mailto:|tel:|javascript:|data:)", href):
            if href.startswith("http"):
                ext += 1
                if not href.startswith("https://"):
                    print("INSECURE", n, href); bad += 1
            continue
        if href.startswith("/"):
            print("ABSOLUTE PATH", n, href); bad += 1; continue
        total += 1
        path, frag = urldefrag(href)
        path = unquote(path)
        target = n if path == "" else path
        tp = ROOT / target
        if not tp.exists():
            print("MISSING FILE", n, "->", href); bad += 1; continue
        if frag and target.endswith(".html"):
            if frag not in info.get(target, L()).ids:
                print("MISSING ANCHOR", n, "->", href); bad += 1
print("internal refs checked: %d, external links: %d, problems: %d" % (total, ext, bad))
sys.exit(1 if bad else 0)
