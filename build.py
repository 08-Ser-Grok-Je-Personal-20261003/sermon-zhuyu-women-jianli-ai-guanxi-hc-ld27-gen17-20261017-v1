#!/usr/bin/env python3
"""Static-site builder for 「主与我们建立爱的关系」.

All text of the three ecumenical creeds and the Three Forms of Unity is inserted
PROGRAMMATICALLY from ./corpus/*.json (scraped verbatim from https://ccifellowship.org)
with HTML-escaping only. Author-written commentary lives in ./src/*.html and may use
directives such as {{HC 74}}, {{BC 34}}, {{DORT 1 17}}, {{CREED apostles}},
{{SENT HC 74 answer | needle}}.  Run:  python3 build.py   (then python3 verify_verbatim.py)
"""
import json, re, html, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
SRC = ROOT / "src"
SITE = "https://ccifellowship.org"
BUILD_DATE = "2026-10-17"
VERSION = "v1"

CREEDS = json.loads((CORPUS / "creeds.json").read_text(encoding="utf-8"))
BELGIC = json.loads((CORPUS / "belgic.json").read_text(encoding="utf-8"))
HEID = json.loads((CORPUS / "heidelberg.json").read_text(encoding="utf-8"))
DORT = json.loads((CORPUS / "dort.json").read_text(encoding="utf-8"))

BC = {a["number"]: a for a in BELGIC["articles"]}
HCQ, HCLD_OF = {}, {}
HCLD = {}
for ld in HEID["lordsdays"]:
    HCLD[ld["number"]] = ld
    for q in ld["questions"]:
        HCQ[q["q"]] = q
        HCLD_OF[q["q"]] = ld
DORT_KEYS = ["1", "2", "34", "5"]            # head page keys (Heads 3&4 are one page on the site)
DORT_HEAD = {k: h for k, h in zip(DORT_KEYS, DORT["heads"])}
DORT_NAMES = {"1": "第一项教义", "2": "第二项教义", "34": "第三、四项教义", "5": "第五项教义"}

CREED_LABEL = {"apostles": "使徒信经", "nicene": "尼西亚信经", "athanasian": "亚他那修信经"}
SIT = lambda s: s  # placeholder (no transformation)


def esc(s):
    return html.escape(s, quote=True)


MARK_RE = re.compile(r"\^(\d+)")


def strip_markers(s):
    return MARK_RE.sub("", s)


def render_inline(raw, marks=None):
    """escape + footnote markers -> <sup>; optional <mark> highlights of exact substrings (no change of text)."""
    spans = []
    for m in (marks or []):
        i = raw.find(m)
        if i < 0:
            raise SystemExit("mark not found in source text: %r" % m)
        spans.append((i, i + len(m)))
    spans.sort()
    out, pos = [], 0

    def seg(t):
        res, p = [], 0
        for mm in MARK_RE.finditer(t):
            res.append(esc(t[p:mm.start()]))
            res.append('<sup class="fn">%s</sup>' % mm.group(1))
            p = mm.end()
        res.append(esc(t[p:]))
        return "".join(res)

    for a, b in spans:
        if a < pos:
            raise SystemExit("overlapping marks")
        out.append(seg(raw[pos:a]))
        out.append('<mark class="hl">%s</mark>' % seg(raw[a:b]))
        pos = b
    out.append(seg(raw[pos:]))
    return "".join(out)


def render_paras(raw, marks=None):
    paras = re.split(r"\n\s*\n", raw.strip())
    return _render_paras_marks(paras, marks or [])


def _render_paras_marks(paras, marks):
    res = []
    remaining = list(marks)
    for p in paras:
        here = [m for m in remaining if p.strip().find(m) >= 0]
        for m in here:
            remaining.remove(m)
        res.append("<p>%s</p>" % render_inline(p.strip(), here))
    if remaining:
        raise SystemExit("mark(s) not found in a single paragraph: %r" % remaining)
    return "".join(res)


def split_dort(text):
    """Dort texts on the site end with '- ref' bullet lines; separate them from the body."""
    parts = re.split(r"\n\n", text)
    refs = []
    while parts and parts[-1].strip().startswith("- ") and len(parts) > 1:
        refs.insert(0, parts.pop().strip()[2:].strip())
    return "\n\n".join(parts), refs


# sanity: dort bullets == refs
for k, h in DORT_HEAD.items():
    for a in h["articles"]:
        body, bl = split_dort(a["text"])
        if bl != a["refs"]:
            # tolerate: some pages have bullets only inside refs list; report
            if bl and a["refs"] and bl != a["refs"]:
                print("WARN dort refs differ", k, a["number"], bl, a["refs"], file=sys.stderr)


def split_sentences(raw):
    """Lossless sentence split (''.join(result) == raw). Keeps closing quotes, bracket and footnote markers with the sentence."""
    out, i, n = [], 0, len(raw)
    start = 0
    while i < n:
        ch = raw[i]
        if ch in "。！？" or ch == "\n":
            j = i + 1
            while j < n and raw[j] in "。！？":
                j += 1
            if ch != "\n":
                while j < n and (raw[j] in "”」’』）)" or raw[j] == "^"):
                    if raw[j] == "^":
                        k = j + 1
                        while k < n and raw[k].isdigit():
                            k += 1
                        j = k
                    else:
                        j += 1
            out.append(raw[start:j])
            start = j
            i = j
        else:
            i += 1
    if start < n:
        out.append(raw[start:])
    return out


def clean_sents(raw):
    return [s for s in split_sentences(raw) if s.strip()]


def field_raw(doc, ident, field):
    if doc == "HC":
        q = HCQ[int(ident[0])]
        return q[field]
    if doc == "BC":
        return BC[int(ident[0])][field]
    if doc == "DORT":
        a = [x for x in DORT_HEAD[ident[0]]["articles"] if x["number"] == int(ident[1])][0]
        if field == "text":
            return split_dort(a["text"])[0]
        return a[field]
    raise KeyError(doc)


# ---------------------------------------------------------------- source links / captions
def hc_src(n):
    return HCLD_OF[n]["url"]


def hc_label(n):
    return "海德堡要理问答 · 主日%d · 问答%d" % (HCLD_OF[n]["number"], n)


def bc_label(n):
    return "比利时信条 · " + BC[n]["title"]


def dort_article(k, n):
    return [x for x in DORT_HEAD[k]["articles"] if x["number"] == n][0]


def dort_label(k, n):
    a = dort_article(k, n)
    return "多特信经 · %s · %s" % (DORT_NAMES[k], a["title"])


def link(url, text="原文 ↗"):
    return '<a class="src" href="%s" target="_blank" rel="noopener">%s</a>' % (esc(url), text)


# ---------------------------------------------------------------- figures
def refs_ol(refs, field_attr=True):
    if not refs:
        return ""
    return '<ol class="vq-refs" data-field="refs">%s</ol>' % "".join("<li>%s</li>" % esc(r) for r in refs)


def fig_hc(n, part="qa", anchor=False):
    q = HCQ[n]
    ld = HCLD_OF[n]
    h = ['<figure class="vq vq-hc" %sdata-doc="HC" data-id="%d" data-source="%s">' % ('id="q%d" ' % n if anchor else "", n, esc(hc_src(n)))]
    h.append('<figcaption><span class="tag creed">HC</span><span>%s</span>%s</figcaption>' % (esc(hc_label(n)), link(hc_src(n))))
    if "q" in part:
        h.append('<div class="vq-q" data-field="question">%s</div>' % render_paras(q["question"]))
    if "a" in part:
        h.append('<div class="vq-a" data-field="answer">%s</div>' % render_paras(q["answer"]))
        h.append(refs_ol(q["refs"]))
    h.append("</figure>")
    return "".join(h)


def fig_bc(n, anchor=False):
    a = BC[n]
    h = ['<figure class="vq vq-bc" %sdata-doc="BC" data-id="%d" data-source="%s">' % ('id="art%d" ' % n if anchor else "", n, esc(a["url"]))]
    h.append('<figcaption><span class="tag grace">BC</span><span>%s</span>%s</figcaption>' % (esc(bc_label(n)), link(a["url"])))
    h.append('<div class="vq-title" data-field="title"><p>%s</p></div>' % render_inline(a["title"]))
    h.append('<div class="vq-t" data-field="text">%s</div>' % render_paras(a["text"]))
    h.append(refs_ol(a["refs"]))
    h.append("</figure>")
    return "".join(h)


def fig_dort(k, n, anchor=False):
    a = dort_article(k, n)
    body, _ = split_dort(a["text"])
    h = ['<figure class="vq vq-dort" %sdata-doc="DORT" data-id="%s.%d" data-source="%s">' % ('id="d%s-%d" ' % (k, n) if anchor else "", k, n, esc(a["url"]))]
    h.append('<figcaption><span class="tag rose">Dort</span><span>%s</span>%s</figcaption>' % (esc(dort_label(k, n)), link(a["url"])))
    h.append('<div class="vq-title" data-field="title"><p>%s</p></div>' % render_inline(a["title"]))
    h.append('<div class="vq-t" data-field="text">%s</div>' % render_paras(body))
    h.append(refs_ol(a["refs"]))
    h.append("</figure>")
    return "".join(h)


def fig_creed(name, marks=None, anchor=False):
    c = CREEDS[name]
    h = ['<figure class="vq vq-creed" %sdata-doc="CREED" data-id="%s" data-source="%s">' % ('id="%s" ' % name if anchor else "", name, esc(c["url"]))]
    h.append('<figcaption><span class="tag creed">信经</span><span>%s</span>%s</figcaption>' % (esc(c["title"]), link(c["url"])))
    h.append('<div class="creed-text" data-field="text">%s</div>' % (render_paras(c["text"], marks) if marks else render_paras(c["text"])))
    h.append("</figure>")
    return "".join(h)


def creed_para(name, idx):
    c = CREEDS[name]
    paras = [p.strip() for p in re.split(r"\n\s*\n", c["text"].strip()) if p.strip()]
    return ('<blockquote class="vs creed" data-doc="CREED" data-id="%s" data-para="%d" data-source="%s">'
            '<span class="vs-text">%s</span><cite>—— %s · <a class="src" href="%s" target="_blank" rel="noopener">原文 ↗</a></cite></blockquote>') % (
        name, idx, esc(c["url"]), render_inline(paras[idx]), esc(c["title"]), esc(c["url"]))


def sent_block(doc, ident, field, needle, marks=None, idx=None):
    raw = field_raw(doc, ident, field)
    sents = clean_sents(raw)
    if needle is not None:
        hit = [s for s in sents if needle in strip_markers(s) or needle in s]
        if len(hit) != 1:
            raise SystemExit("SENT needle %r in %s %s %s matched %d sentences: %s" % (needle, doc, ident, field, len(hit), hit))
        s = hit[0]
    else:
        s = sents[idx]
    s = s.strip()
    if doc == "HC":
        n = int(ident[0]); src = hc_src(n); cls = "hc"; lab = "%s · %s" % (hc_label(n), "问" if field == "question" else "答")
    elif doc == "BC":
        n = int(ident[0]); src = BC[n]["url"]; cls = "bc"; lab = bc_label(n)
    else:
        k, n = ident[0], int(ident[1]); src = dort_article(k, n)["url"]; cls = "dort"; lab = dort_label(k, n)
    return ('<blockquote class="vs %s" data-doc="%s" data-id="%s" data-field="%s" data-source="%s">'
            '<span class="vs-text">%s</span><cite>—— %s · %s</cite></blockquote>') % (
        cls, doc, ".".join(ident), field, esc(src), render_inline(s, marks), esc(lab), link(src))


# ---------------------------------------------------------------- data blobs
def json_script(sid, obj, source):
    s = json.dumps(obj, ensure_ascii=False)
    s = s.replace("</", "<\\/")
    return '<script type="application/json" id="%s" data-source="%s">%s</script>' % (sid, esc(source), s)


def data_blob(name):
    if name == "creeds":
        return json_script("creeds-data", {k: {"title": v["title"], "text": v["text"], "url": v["url"]} for k, v in CREEDS.items()}, SITE + "/books/book-of-praise/creeds")
    if name == "hc74":
        raw = strip_markers(HCQ[74]["answer"])
        return json_script("hc74-data", {"q": 74, "field": "answer", "sentences": [s.strip() for s in clean_sents(raw)], "url": hc_src(74)}, hc_src(74))
    raise KeyError(name)


# ---------------------------------------------------------------- icons
ICONS = {
 "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 5.5v16M8 7h8M8 11h6"/>',
 "scroll": '<path d="M7 3h11a2 2 0 0 1 2 2v2h-3v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-1h10v1a1 1 0 0 0 1 1"/><path d="M7 3a2 2 0 0 0-2 2v13M9 8h5M9 12h5"/>',
 "cross": '<path d="M12 3v18M6.5 9h11"/>',
 "drop": '<path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z"/><path d="M9.5 14.5a2.6 2.6 0 0 0 2.5 2.5" />',
 "ring": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.4"/>',
 "circle": '<circle cx="12" cy="12" r="8.5"/>',
 "family": '<circle cx="8" cy="7" r="2.6"/><circle cx="16.5" cy="7.5" r="2.2"/><path d="M3.5 19v-2.5A4 4 0 0 1 7.5 12.5h1A4 4 0 0 1 12.5 16.5V19M13 19v-2a3.4 3.4 0 0 1 3.4-3.4h.2A3.4 3.4 0 0 1 20 17v2"/>',
 "baby": '<circle cx="12" cy="8" r="4"/><path d="M5 20c.6-3.6 3.4-5.5 7-5.5s6.4 1.9 7 5.5"/><path d="M10.5 8h.01M13.5 8h.01M10.8 9.8c.7.6 1.7.6 2.4 0"/>',
 "hand": '<path d="M8 12V6a1.5 1.5 0 0 1 3 0v5M11 11V4.5a1.5 1.5 0 0 1 3 0V11M14 11V6a1.5 1.5 0 0 1 3 0v8a6 6 0 0 1-6 6h-.5a5 5 0 0 1-4-2l-3-4.2a1.5 1.5 0 0 1 2.3-1.9L8 14"/>',
 "pin": '<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
 "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
 "tree": '<path d="M12 21v-7M12 14c-4 0-6.5-3-5.5-6.2C7.4 5 10.5 4 12 2c1.5 2 4.6 3 5.5 5.8C18.5 11 16 14 12 14z"/>',
 "hourglass": '<path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9"/>',
 "shield": '<path d="M12 3l7.5 3v5.5c0 4.6-3.2 8-7.5 9.5-4.3-1.5-7.5-4.9-7.5-9.5V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
 "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
 "heart": '<path d="M12 20s-8-4.8-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.2 12 20 12 20z"/>',
 "crown": '<path d="M3.5 18.5h17l1-11-5 4-4.5-7-4.5 7-5-4z"/>',
 "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
 "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.2l2.7 2.8L16.3 9"/>',
 "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.6 2.6 0 1 1 3.6 2.4c-.8.4-1.1 1-1.1 1.8M12 17h.01"/>',
 "bulb": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>',
 "warn": '<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4.5M12 17.4h.01"/>',
 "bookmark": '<path d="M6 3h12v18l-6-4.5L6 21z"/>',
 "pen": '<path d="M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z"/><path d="M14.5 6.5l3 3"/>',
 "bell": '<path d="M6 17V11a6 6 0 0 1 12 0v6l1.5 2h-15zM10 21h4"/>',
 "music": '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
 "church": '<path d="M12 2v5M10 4.5h4M12 7l6 4v10H6V11zM10 21v-5h4v5M3 21h18"/>',
 "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
 "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
 "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
 "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
 "toc": '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
 "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
 "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.3 0 2-.8 2-1.8 0-1.2-1-1.4-1-2.5 0-1 .8-1.7 1.8-1.7H17a4 4 0 0 0 4-4C21 6.9 17 3 12 3z"/><path d="M7.5 11h.01M10 7.5h.01M14.5 7.5h.01"/>',
 "scale": '<path d="M12 3v18M6 21h12M5 7h14M5 7l-2.5 6a3 3 0 0 0 5 0zM19 7l-2.5 6a3 3 0 0 0 5 0z"/>',
 "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/>',
 "seal": '<circle cx="12" cy="9" r="6"/><path d="M8.5 14.5L7 21l5-3 5 3-1.5-6.5"/><path d="M9.5 9l1.8 1.8L15 7.5"/>',
 "people": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.3"/><path d="M3 19c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14c3 0 6 1.4 6 5"/>',
 "sprout": '<path d="M12 21v-9M12 12C12 8 9 6 5 6c0 4 2.5 6 7 6zM12 14c0-3 2-5 6-5 0 3.5-2 5-6 5z"/>',
 "path": '<path d="M5 21c0-5 14-5 14-10S5 7 5 3M12 3v2M12 8v2M12 15v2"/>',
 "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
 "flag": '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
 "layers": '<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/>',
 "list": '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
 "mountain": '<path d="M2.5 20l7-12 4 6 2.5-4 5.5 10z"/>',
 "brain": '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 5 1.5V5A2 2 0 0 0 9 4zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-5 1.5V5a2 2 0 0 1 2-1z"/>',
 "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
 "up": '<path d="M12 19V6M6 11l6-6 6 6"/>',
 "print": '<path d="M7 9V3h10v6M6 17H4v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6h-2M7 14h10v7H7z"/>',
 "shuffle": '<path d="M3 7h3c5 0 6 10 11 10h4M3 17h3c1.7 0 2.9-.9 3.9-2.2M21 7h-4c-1.7 0-2.9.9-3.9 2.2M18.5 4.5L21 7l-2.5 2.5M18.5 14.5L21 17l-2.5 2.5"/>',
 "text": '<path d="M5 6V4h14v2M12 4v16M9 20h6"/>',
 "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
 "bolt": '<path d="M13 2L4.5 13.5H11L10 22l8.5-11.5H12z"/>',
 "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
}


def sprite():
    syms = "".join('<symbol id="i-%s" viewBox="0 0 24 24">%s</symbol>' % (k, v) for k, v in ICONS.items())
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>%s</defs></svg>' % syms


def icon(name, cls=""):
    if name not in ICONS:
        raise SystemExit("unknown icon " + name)
    return '<svg class="ic %s" aria-hidden="true" focusable="false"><use href="#i-%s"/></svg>' % (cls, name)


CO_ICON = {"key": "star", "hard": "mountain", "mem": "bookmark", "warn": "warn", "info": "info", "ok": "check"}
CO_NAME = {"key": "重点", "hard": "难点", "mem": "记忆", "warn": "警戒", "info": "提示", "ok": "恩典"}

# ---------------------------------------------------------------- stats
def creed_chars(name):
    return len(re.sub(r"\s", "", CREEDS[name]["text"]))


def creed_lines(name):
    t = CREEDS[name]["text"]
    if name == "athanasian":
        return len(re.findall(r"\d+\)", t))
    return len([p for p in re.split(r"\n\s*\n", t) if p.strip()])


def dort_total():
    return sum(len(h["articles"]) for h in DORT["heads"])


VARS = {
    "n_apostles": lambda: creed_chars("apostles"),
    "n_nicene": lambda: creed_chars("nicene"),
    "n_athanasian": lambda: creed_chars("athanasian"),
    "l_apostles": lambda: creed_lines("apostles"),
    "l_nicene": lambda: creed_lines("nicene"),
    "l_athanasian": lambda: creed_lines("athanasian"),
    "n_bc": lambda: len(BELGIC["articles"]),
    "n_hcq": lambda: len(HCQ),
    "n_hcld": lambda: len(HCLD),
    "n_dort_heads": lambda: len(DORT["heads"]),
    "n_dort_art": lambda: dort_total(),
    "n_dort_art_1": lambda: len(DORT_HEAD["1"]["articles"]),
    "n_dort_art_2": lambda: len(DORT_HEAD["2"]["articles"]),
    "n_dort_art_34": lambda: len(DORT_HEAD["34"]["articles"]),
    "n_dort_art_5": lambda: len(DORT_HEAD["5"]["articles"]),
    "chars_hc": lambda: sum(len(re.sub(r"\s", "", strip_markers(q["question"] + q["answer"]))) for q in HCQ.values()),
    "chars_bc": lambda: sum(len(re.sub(r"\s", "", strip_markers(a["text"]))) for a in BC.values()),
    "chars_dort": lambda: sum(len(re.sub(r"\s", "", strip_markers(split_dort(a["text"])[0]))) for h in DORT["heads"] for a in h["articles"]),
    "date": lambda: BUILD_DATE,
    "version": lambda: VERSION,
}

# ---------------------------------------------------------------- directives
DIRECTIVE = re.compile(r"\{\{\s*([A-Z0-9_]+)([^{}]*)\}\}")


def hc_ld_block(n):
    ld = HCLD[n]
    qs = [q["q"] for q in ld["questions"]]
    return "".join(fig_hc(q) for q in qs)


def run_directive(m):
    name, arg = m.group(1), m.group(2).strip()
    left, _, right = arg.partition("|")
    toks = left.split()
    if name == "HC":
        part = toks[1] if len(toks) > 1 else "qa"
        part = {"q": "q", "a": "a", "qa": "qa"}[part]
        return fig_hc(int(toks[0]), part)
    if name == "HCLD":
        return hc_ld_block(int(toks[0]))
    if name == "BC":
        return fig_bc(int(toks[0]))
    if name == "DORT":
        return fig_dort(toks[0], int(toks[1]))
    if name == "CREED":
        marks = [x.strip() for x in right.split(";") if x.strip()] if right else None
        return fig_creed(toks[0], marks)
    if name == "SENT":
        needle, _, marks = right.partition("||")
        needle = needle.strip()
        mk = [x.strip() for x in marks.split(";") if x.strip()] if marks else None
        doc = toks[0]
        if doc == "HC":
            return sent_block("HC", [toks[1]], toks[2], needle, mk)
        if doc == "BC":
            return sent_block("BC", [toks[1]], toks[2] if len(toks) > 2 else "text", needle, mk)
        if doc == "DORT":
            return sent_block("DORT", [toks[1], toks[2]], toks[3] if len(toks) > 3 else "text", needle, mk)
    if name == "CPARA":
        return creed_para(toks[0], int(toks[1]))
    if name == "DATA":
        return data_blob(toks[0])
    if name == "VAR":
        return str(VARS[toks[0]]())
    if name == "I":
        return icon(toks[0], " ".join(toks[1:]))
    if name == "INC":
        return process(read_src("_inc/" + toks[0] + ".html"))
    raise SystemExit("unknown directive: " + m.group(0))


CO_RE = re.compile(r"^:::[ \t]*(key|hard|mem|warn|info|ok)[ \t]*(.*?)\n(.*?)\n:::[ \t]*$", re.S | re.M)


def expand_callouts(t):
    def f(m):
        kind, title, content = m.group(1), m.group(2).strip() or CO_NAME[m.group(1)], m.group(3)
        return '<div class="co %s rv">%s<div><b class="t">%s</b>%s</div></div>' % (kind, icon(CO_ICON[kind]), title, content)
    return CO_RE.sub(f, t)


def process(text):
    text = expand_callouts(text)
    return DIRECTIVE.sub(run_directive, text)


# ---------------------------------------------------------------- layout
NAV = [
    ("index.html", "首页", "church"),
    ("sermon.html", "讲章", "book"),
    ("creeds-read.html", "信经阅读", "scroll"),
    ("forms-read.html", "三项信条", "layers"),
    ("compare.html", "信经比较", "scale"),
    ("covenant-baptism.html", "圣约与洗礼", "drop"),
    ("memorize.html", "背诵", "brain"),
    ("resources.html", "资源", "link"),
]
LOGO = ('<svg class="logo" viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e2b53e"/><stop offset="1" stop-color="#b7860b"/></linearGradient></defs>'
        '<circle cx="16" cy="16" r="13" fill="none" stroke="url(#lg)" stroke-width="2.6"/><path d="M16 8c3 3.4 4.6 5.6 4.6 8a4.6 4.6 0 0 1-9.2 0c0-2.4 1.6-4.6 4.6-8z" fill="#1c78b8"/><path d="M16 14.2c1.2 1.4 1.9 2.4 1.9 3.4a1.9 1.9 0 0 1-3.8 0c0-1 .7-2 1.9-3.4z" fill="#b3202a"/></svg>')


def heading_toc(body):
    items = []
    for m in re.finditer(r'<h([23])\s+id="([^"]+)"[^>]*>(.*?)</h\1>', body, re.S):
        lvl, hid, inner = m.group(1), m.group(2), m.group(3)
        inner = re.sub(r"<svg.*?</svg>", "", inner, flags=re.S)
        inner = re.sub(r"<[^>]+>", "", inner)
        inner = html.unescape(inner).strip()
        if inner:
            items.append((lvl, hid, inner))
    return items


LIVE_FOOT = ('<div class="live">线上链接 / Live links：'
             '<a href="https://08-ser-grok-je-personal-20261003.github.io/sermon-zhuyu-women-jianli-ai-guanxi-hc-ld27-gen17-20261017-v1/" target="_blank" rel="noopener">GitHub Pages</a> · '
             '<a href="https://sermon-zhuyu-women-jianli-ai-guanxi-hc-ld27-gen17-20261017-v1.surge.sh" target="_blank" rel="noopener">Surge</a> · '
             '<a href="https://github.com/08-Ser-Grok-Je-Personal-20261003/sermon-zhuyu-women-jianli-ai-guanxi-hc-ld27-gen17-20261017-v1" target="_blank" rel="noopener">Repository</a></div>')


def layout(fname, title, desc, body, toc=True, bodycls=""):
    items = heading_toc(body) if toc else []
    has_toc = toc and items
    nav = "".join('<a href="%s"%s>%s<span>%s</span></a>' % (f, ' aria-current="page"' if f == fname or (fname in ("hc.html", "belgic.html", "dort.html") and f == "forms-read.html") else "", icon(ic), esc(lbl)) for f, lbl, ic in NAV)
    toc_html = ""
    if has_toc:
        toc_html = ('<aside id="toc" class="toc" aria-label="目录"><h2><span>%s 目录</span><button class="hbtn toc-close" type="button" aria-label="关闭目录">×</button></h2><nav>%s</nav></aside><div class="toc-scrim"></div>'
                    % (icon("toc"), "".join('<a class="l%s" href="#%s">%s</a>' % (l, i, esc(t)) for l, i, t in items)))
    toc_btn = '<button id="toc-btn" class="hbtn" type="button" aria-controls="toc" aria-expanded="false">%s<span class="lbl">目录</span></button>' % icon("toc") if has_toc else ""
    head = ('<!DOCTYPE html>\n<html lang="zh-Hans" data-theme="parchment">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<title>%s · 主与我们建立爱的关系</title>\n<meta name="description" content="%s">\n<meta name="theme-color" content="#0e1a2b">\n'
            '<script>(function(){try{var t=localStorage.getItem("zw-theme");if(!t)t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"parchment";document.documentElement.setAttribute("data-theme",t)}catch(e){}})()</script>\n'
            '<link rel="stylesheet" href="assets/style.css">\n</head>\n') % (esc(title), esc(desc))
    hdr = ('<body class="%s" data-toc="closed">\n%s\n<div id="progress" aria-hidden="true"></div>\n'
           '<header class="hdr"><a class="brand" href="index.html" aria-label="首页">%s<span>主与我们建立爱的关系</span></a>'
           '<nav class="nav" id="nav" aria-label="主导航">%s</nav>'
           '<div class="hdr-tools">%s<button id="theme-btn" class="hbtn" type="button">%s<span class="lbl">羊皮纸</span></button>'
           '<button id="nav-btn" class="hbtn only-m" type="button" aria-controls="nav" aria-expanded="false" aria-label="菜单">%s</button></div></header>\n') % (bodycls, sprite(), LOGO, nav, toc_btn, icon("palette"), icon("menu"))
    live = LIVE_FOOT if fname in ("index.html", "resources.html") else ""
    foot = ('<footer class="ftr"><div>主与我们建立爱的关系 · 海德堡要理问答主日27（问72–74）· 创世记17章 · %s · 最后更新 %s（Asia/Taipei）</div>'
            '<div>三大普世信经与三项联合信条的原文均由构建脚本从 <a href="%s" target="_blank" rel="noopener">ccifellowship.org</a> 的存档逐字载入；讲章与解说为本站作者自撰。</div>'
            '%s<div><a href="resources.html">资源与出处</a> · <a href="#top">回到顶部</a></div></footer>\n'
            '<button id="totop" type="button" aria-label="回到顶部">%s</button>\n') % (VERSION, BUILD_DATE, SITE, live, icon("up"))
    scripts = '<script src="assets/app.js" defer></script>\n'
    extra = PAGE_SCRIPTS.get(fname, [])
    for s in extra:
        scripts += '<script src="assets/%s" defer></script>\n' % s
    layout_cls = "layout has-toc" if has_toc else "layout"
    main = '<div class="%s">%s<main id="main" class="main">%s</main></div>\n' % (layout_cls, toc_html, body)
    return head + hdr + '<a id="top"></a>' + main + foot + scripts + "</body>\n</html>\n"


PAGE_SCRIPTS = {
    "creeds-read.html": ["creeds.js"],
    "forms-read.html": ["forms.js"],
    "hc.html": ["forms.js"],
    "belgic.html": ["forms.js"],
    "dort.html": ["forms.js"],
    "memorize.html": ["memorize.js"],
}

PAGES = {
    "index.html": ("首页", "海德堡要理问答主日27与创世记17章：主与我们建立爱的关系——欧陆改革宗主日讲章与学习站", False),
    "sermon.html": ("讲章", "欧陆改革宗主日讲章：主与我们建立爱的关系（创17；HC主日27）", True),
    "creeds-read.html": ("三大普世信经 · 阅读与背诵", "使徒信经、尼西亚信经、亚他那修信经——干净阅读版与背诵模式（原文取自ccifellowship.org）", True),
    "forms-read.html": ("三项联合信条 · 阅读入口", "海德堡要理问答、比利时信条、多特信经 全文阅读入口", False),
    "compare.html": ("三大信经与三项信条比较", "三大普世信经与三项联合信条的来源、问题、结构与相互关系", True),
    "covenant-baptism.html": ("圣约与洗礼 · 资料卷", "创世记17章流程、圣约时间线、割礼与洗礼对照、HC问69–75、比利时信条34、多特I.17、常见异议", True),
    "memorize.html": ("速记中心", "闪卡、要点、HC问74、信经测验与可打印一页纸", True),
    "resources.html": ("延伸阅读与出处", "ccifellowship.org 链接与其他改革宗机构的延伸阅读", False),
}


def read_src(name):
    return (SRC / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- forms pages (generated)
HC_PART = lambda n: ("导论" if n == 1 else "第一部分 · 人的悲惨" if n <= 4 else "第二部分 · 人的救赎" if n <= 31 else "第三部分 · 感恩")


def build_hc():
    chips = "".join('<a href="#ld%d" data-ld="%d">%d</a>' % (n, n, n) for n in HCLD)
    items = []
    for n, ld in HCLD.items():
        qs = [q["q"] for q in ld["questions"]]
        head = '<h2 id="ld%d" class="ld-h">%s <span class="chip gold">问%s</span> <span class="chip water">%s</span></h2>' % (n, esc(ld["title"]), ("%d–%d" % (qs[0], qs[-1])) if len(qs) > 1 else str(qs[0]), HC_PART(n))
        figs = "".join(fig_hc(q, "qa", anchor=True) for q in qs)
        items.append('<section class="item" data-ld="%d">%s%s</section>' % (n, head, figs))
    body = ('<div class="sec"><h1 style="font-size:clamp(1.6rem,1.2rem+2vw,2.4rem)">海德堡要理问答 · 全文（52主日 / 129问）</h1>'
            '<p class="muted">全文由脚本从 corpus/heidelberg.json 逐字载入（来源 <a href="%s" target="_blank" rel="noopener">ccifellowship.org</a>）。脚注标记以上标显示，引用经文列于每问之下。'
            '“主日”分段采用传统的52主日划分；「部分」标签为本站所加的导航标签。</p>'
            '<div class="ctrl" style="justify-content:flex-start"><input class="search" id="q-search" type="search" placeholder="搜索关键词（如：圣约、洗礼、安慰）…" aria-label="搜索"><label>跳到问答 <input id="jump-n" type="number" min="1" max="129" value="74" style="width:5.5em;padding:.4rem;border-radius:10px;border:1px solid var(--line);background:var(--solid);color:var(--text)"></label><button type="button" class="pri" id="jump-go">前往</button><span class="chip grace" id="count" aria-live="polite"></span></div>'
            '<div class="jump" id="jump" role="navigation" aria-label="主日跳转">%s</div>'
            '<div class="co info rv">%s<div><b class="t">提示</b><p>本页含 52 个主日，已启用渲染优化。本主日讲章所用：<a href="#ld26">主日26</a> · <a href="#ld27">主日27</a> · <a href="#ld28">主日28</a>。原站对问答25/47/63的脚注标记与引用条数不一致、问88/123 有标记无引用列表，均按原样呈现，未作更改。</p></div></div>'
            '%s</div>') % (esc(HEID["url"]), chips, icon("info"), "".join(items))
    return body


def build_belgic():
    chips = "".join('<a href="#art%d">%d</a>' % (n, n) for n in BC)
    items = "".join('<section class="item" data-n="%d">%s</section>' % (n, fig_bc(n, anchor=True)) for n in BC)
    return ('<div class="sec"><h1 style="font-size:clamp(1.6rem,1.2rem+2vw,2.4rem)">比利时信条 · 全文（37条）</h1>'
            '<p class="muted">全文由脚本从 corpus/belgic.json 逐字载入（来源 <a href="%s" target="_blank" rel="noopener">ccifellowship.org</a>）。第34条《论圣洗礼》为本主日相关条文：<a href="#art34">跳转</a>。</p>'
            '<div class="ctrl" style="justify-content:flex-start"><input class="search" id="q-search" type="search" placeholder="搜索关键词（如：洗礼、教会、圣经）…" aria-label="搜索"><span class="chip grace" id="count" aria-live="polite"></span></div>'
            '<div class="jump" id="jump" role="navigation" aria-label="条文跳转">%s</div>%s</div>') % (esc(BELGIC["url"]), chips, items)


def build_dort():
    chips = []
    sections = []
    for k in DORT_KEYS:
        h = DORT_HEAD[k]
        chips.append('<a href="#h%s">%s</a>' % (k, {"1": "第一项", "2": "第二项", "34": "第三、四项", "5": "第五项"}[k]))
        arts = "".join('<section class="item" data-n="%s">%s</section>' % (a["number"], fig_dort(k, a["number"], anchor=True)) for a in h["articles"])
        art_chips = "".join('<a href="#d%s-%d">%s</a>' % (k, a["number"], a["number"] if not a["title"].startswith("错谬") else "错谬") for a in h["articles"])
        sections.append('<section class="sec" id="h%s"><h2 id="h%s-t">%s <a class="src" style="font-size:.8rem;font-family:var(--sans)" href="%s" target="_blank" rel="noopener">原站 ↗</a></h2><div class="jump" style="position:static">%s</div>%s</section>' % (k, k, esc(h["title"]), esc(h["url"]), art_chips, arts))
    return ('<div class="sec"><h1 style="font-size:clamp(1.6rem,1.2rem+2vw,2.4rem)">多特信经 · 全文（四项教义页）</h1>'
            '<p class="muted">全文由脚本从 corpus/dort.json 逐字载入（来源 <a href="%s" target="_blank" rel="noopener">ccifellowship.org</a>）。该站将第三、四项教义合并为一页，故共四页；“错谬反驳”为各项的末条。《多特信经》第一项第17条《死于婴幼期的信徒儿女》为本主日相关条文：<a href="#d1-17">跳转</a>。</p>'
            '<div class="ctrl" style="justify-content:flex-start"><input class="search" id="q-search" type="search" placeholder="搜索关键词（如：圣约、拣选、儿女）…" aria-label="搜索"><span class="chip grace" id="count" aria-live="polite"></span></div>'
            '<div class="jump" id="jump" role="navigation" aria-label="教义跳转">%s</div></div>%s') % (esc(DORT["url"]), "".join(chips), "".join(sections))


# ---------------------------------------------------------------- main
def main():
    out = {}
    for fname, (title, desc, toc) in PAGES.items():
        if not (SRC / fname).exists():
            print("SKIP (no src)", fname)
            continue
        body = process(read_src(fname))
        out[fname] = layout(fname, title, desc, body, toc)
    out["hc.html"] = layout("hc.html", "海德堡要理问答 全文", "海德堡要理问答52主日129问全文阅读", process(build_hc()), toc=False)
    out["belgic.html"] = layout("belgic.html", "比利时信条 全文", "比利时信条37条全文阅读", process(build_belgic()), toc=False)
    out["dort.html"] = layout("dort.html", "多特信经 全文", "多特信经四页全文阅读", process(build_dort()), toc=False)
    for fname, content in out.items():
        (ROOT / fname).write_text(content, encoding="utf-8")
        print("wrote %-24s %8.1f KB" % (fname, len(content.encode("utf-8")) / 1024))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sent":
        doc, ident, field = sys.argv[2], sys.argv[3], sys.argv[4]
        raw = field_raw(doc, ident.split("."), field)
        for i, s in enumerate(clean_sents(raw)):
            print(i, repr(s.strip()))
    else:
        main()
