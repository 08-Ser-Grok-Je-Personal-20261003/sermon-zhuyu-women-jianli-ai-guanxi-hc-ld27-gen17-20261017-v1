#!/usr/bin/env python3
"""verify_verbatim.py — independent check that every quotation of the three ecumenical creeds and the
Three Forms of Unity in the built HTML equals the text in corpus/*.json.

It does NOT import build.py. It parses each *.html file and compares:
  * <figure data-doc> blocks: each data-field div (question/answer/title/text) == JSON field
    (paragraphs joined by a blank line, <sup> footnote numbers removed, whitespace at paragraph edges ignored);
    footnote numbers shown == the ^N markers in the JSON; the refs list == JSON refs; data-source present.
  * <blockquote class="vs"> short quotes: whole sentence(s) of the stated field (or a whole creed paragraph).
  * JSON blobs (#creeds-data, #hc74-data) == corpus.
  * Leak scan: no run of >= 14 characters from the corpus appears in author text outside quote blocks.
Exit code 0 only if everything PASSes.
"""
import json, re, sys, html
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
C = ROOT / "corpus"
CREEDS = json.loads((C / "creeds.json").read_text("utf-8"))
BEL = json.loads((C / "belgic.json").read_text("utf-8"))
HEI = json.loads((C / "heidelberg.json").read_text("utf-8"))
DOR = json.loads((C / "dort.json").read_text("utf-8"))

MARK = re.compile(r"\^(\d+)")
BC = {a["number"]: a for a in BEL["articles"]}
HCQ = {}
for ld in HEI["lordsdays"]:
    for q in ld["questions"]:
        HCQ[q["q"]] = q
KEYS = ["1", "2", "34", "5"]
DH = {k: h for k, h in zip(KEYS, DOR["heads"])}


def split_dort(text):
    parts = text.split("\n\n")
    refs = []
    while parts and parts[-1].strip().startswith("- ") and len(parts) > 1:
        refs.insert(0, parts.pop().strip()[2:].strip())
    return "\n\n".join(parts), refs


def expected_field(doc, ident, field):
    """returns (raw_with_markers, refs or None)"""
    if doc == "HC":
        q = HCQ[int(ident)]
        return q[field], q["refs"]
    if doc == "BC":
        a = BC[int(ident)]
        return a[field], a["refs"]
    if doc == "DORT":
        k, n = ident.split(".")
        a = [x for x in DH[k]["articles"] if x["number"] == int(n)][0]
        if field == "text":
            return split_dort(a["text"])[0], a["refs"]
        return a[field], a["refs"]
    if doc == "CREED":
        return CREEDS[ident][field], None
    raise KeyError(doc)


def paras(raw):
    return [p.strip() for p in re.split(r"\n\s*\n", raw.strip())]


def plain(raw):
    return "\n\n".join(MARK.sub("", p) for p in paras(raw))


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.figs = []        # dict(doc,id,source,fields{name:{paras,sups}}, refs[])
        self.vs = []          # dict(doc,id,field,para,source,text,sups)
        self.blobs = {}
        self.cur_fig = None
        self.cur_field = None  # (name, dict)
        self.cur_vs = None
        self.in_vs_text = False
        self.cur_p = None
        self.in_sup = 0
        self.in_refs = None
        self.in_li = None
        self.in_script = None
        self.outside = []     # visible author text
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        self.stack.append((tag, a))
        if tag == "script":
            self.in_script = (a.get("id"), [])
            return
        if tag == "style":
            self.in_style = True
        if tag == "figure" and "data-doc" in a:
            self.cur_fig = dict(doc=a["data-doc"], id=a.get("data-id"), source=a.get("data-source"), fields={}, refs=None)
            self.figs.append(self.cur_fig)
        if tag == "blockquote" and "vs" in cls and "data-doc" in a:
            self.cur_vs = dict(doc=a["data-doc"], id=a.get("data-id"), field=a.get("data-field"), para=a.get("data-para"),
                               source=a.get("data-source"), text="", sups=[])
            self.vs.append(self.cur_vs)
        if self.cur_vs is not None and tag == "span" and "vs-text" in cls:
            self.in_vs_text = True
        if self.cur_fig is not None and tag == "div" and "data-field" in a:
            d = dict(paras=[], sups=[])
            self.cur_fig["fields"][a["data-field"]] = d
            self.cur_field = d
        if self.cur_fig is not None and tag == "ol" and a.get("data-field") == "refs":
            self.cur_fig["refs"] = []
            self.in_refs = self.cur_fig["refs"]
        if self.in_refs is not None and tag == "li":
            self.in_li = []
        if self.cur_field is not None and tag == "p":
            self.cur_p = []
        if tag == "sup":
            self.in_sup += 1
            self._sup = []

    def handle_endtag(self, tag):
        while self.stack and self.stack[-1][0] != tag:
            self.stack.pop()
        if self.stack:
            _, a = self.stack.pop()
        else:
            a = {}
        if tag == "script" and self.in_script is not None:
            self.blobs[self.in_script[0]] = "".join(self.in_script[1])
            self.in_script = None
        if tag == "style":
            self.in_style = False
        if tag == "sup" and self.in_sup:
            self.in_sup -= 1
            s = "".join(self._sup).strip()
            if self.in_vs_text and self.cur_vs is not None:
                self.cur_vs["sups"].append(s)
            elif self.cur_field is not None:
                self.cur_field["sups"].append(s)
        if tag == "p" and self.cur_p is not None and self.cur_field is not None:
            self.cur_field["paras"].append("".join(self.cur_p))
            self.cur_p = None
        if tag == "div" and "data-field" in a and self.cur_field is not None:
            self.cur_field = None
        if tag == "li" and self.in_li is not None:
            self.in_refs.append("".join(self.in_li))
            self.in_li = None
        if tag == "ol" and self.in_refs is not None:
            self.in_refs = None
        if tag == "span" and self.in_vs_text and (a.get("class") or "").split().count("vs-text"):
            self.in_vs_text = False
        if tag == "blockquote" and self.cur_vs is not None:
            self.cur_vs = None
        if tag == "figure" and self.cur_fig is not None:
            self.cur_fig = None

    def handle_data(self, data):
        if self.in_script is not None:
            self.in_script[1].append(data)
            return
        if self.in_style:
            return
        if self.in_sup:
            self._sup.append(data)
            return
        if self.in_vs_text and self.cur_vs is not None:
            self.cur_vs["text"] += data
            return
        if self.in_li is not None:
            self.in_li.append(data)
            return
        if self.cur_p is not None:
            self.cur_p.append(data)
            return
        if self.cur_fig is not None or self.cur_vs is not None:
            return  # captions / cite
        self.outside.append(data)


results = []  # (page, kind, label, ok, detail)


def rec(page, kind, label, ok, detail=""):
    results.append((page, kind, label, ok, detail))


def find_raw_span(raw, quote_plain):
    """find quote_plain inside raw allowing ^N markers between chars; returns raw substring or None."""
    pat = "(?:\\^\\d+)?".join(re.escape(ch) for ch in quote_plain)
    m = re.search(pat, raw)
    return m


def check_fig(page, f):
    lab = "%s %s" % (f["doc"], f["id"])
    if not f["source"] or not f["source"].startswith("http"):
        rec(page, "figure", lab, False, "missing data-source")
        return
    ok_all = True
    for name, d in f["fields"].items():
        raw, refs = expected_field(f["doc"], f["id"], name)
        got = "\n\n".join(d["paras"])
        exp = plain(raw)
        if got != exp:
            ok_all = False
            # locate first difference
            i = next((k for k in range(min(len(got), len(exp))) if got[k] != exp[k]), min(len(got), len(exp)))
            rec(page, "figure", "%s/%s" % (lab, name), False, "diff at %d: got %r exp %r" % (i, got[i - 5:i + 15], exp[i - 5:i + 15]))
            continue
        exp_sups = MARK.findall(raw)
        if d["sups"] != exp_sups:
            ok_all = False
            rec(page, "figure", "%s/%s" % (lab, name), False, "footnote numbers %r != %r" % (d["sups"], exp_sups))
    if f["fields"] and f["doc"] != "CREED":
        _, refs = expected_field(f["doc"], f["id"], list(f["fields"])[0])
        if "answer" in f["fields"] or "text" in f["fields"]:
            if (f["refs"] or []) != (refs or []):
                ok_all = False
                rec(page, "figure", lab + "/refs", False, "refs list differs")
    rec(page, "figure", lab, ok_all, "")


SENT_END = "。！？”」’』）)"


def check_vs(page, v):
    lab = "%s %s%s" % (v["doc"], v["id"], "" if not v["field"] else "/" + v["field"])
    if not v["source"] or not v["source"].startswith("http"):
        rec(page, "short", lab, False, "missing data-source")
        return
    text = v["text"].strip()
    if v["doc"] == "CREED":
        ps = paras(CREEDS[v["id"]]["text"])
        exp = MARK.sub("", ps[int(v["para"])])
        rec(page, "short", lab + " ¶%s" % v["para"], text == exp, "" if text == exp else "mismatch")
        return
    raw, _ = expected_field(v["doc"], v["id"], v["field"])
    m = find_raw_span(raw, text)
    if not m:
        rec(page, "short", lab, False, "quote not found in source: %r" % text[:40])
        return
    # whole sentence: starts at field start or after sentence end/newline; ends at sentence end / field end
    before = MARK.sub("", raw[:m.start()]).rstrip()
    ok_start = (before == "") or before[-1] in SENT_END
    after = raw[m.end():]
    after = re.sub(r"^(?:\^\d+)+", "", after)  # trailing footnote markers belong to the sentence
    ok_end = (text[-1] in SENT_END) or after.strip() == ""
    sups_exp = MARK.findall(m.group(0))
    ok_sup = v["sups"] == sups_exp or v["sups"] == sups_exp + MARK.findall(raw[m.end():m.end() + len(raw)])[:0]
    # allow trailing marker captured after the end (markers right after final punctuation)
    tail = re.match(r"^((?:\^\d+)+)", raw[m.end():])
    if tail:
        t = MARK.findall(tail.group(1))
        ok_sup = ok_sup or v["sups"] == sups_exp + t
    ok = ok_start and ok_end and ok_sup
    d = []
    if not ok_start: d.append("not at sentence start")
    if not ok_end: d.append("not at sentence end")
    if not ok_sup: d.append("sup %r vs %r" % (v["sups"], sups_exp))
    rec(page, "short", lab, ok, "; ".join(d))


def check_blobs(page, blobs):
    if "creeds-data" in blobs:
        got = json.loads(blobs["creeds-data"])
        exp = {k: {"title": v["title"], "text": v["text"], "url": v["url"]} for k, v in CREEDS.items()}
        rec(page, "blob", "creeds-data", got == exp, "" if got == exp else "differs")
    if "hc74-data" in blobs:
        got = json.loads(blobs["hc74-data"])
        ans = MARK.sub("", HCQ[74]["answer"])
        j = "".join(got["sentences"])
        ok = re.sub(r"\s", "", j) == re.sub(r"\s", "", ans) and all(s in ans for s in got["sentences"])
        rec(page, "blob", "hc74-data", ok, "" if ok else "differs")


def build_ngrams(n=14):
    texts = []
    for k, v in CREEDS.items():
        texts.append(v["text"])
    for a in BEL["articles"]:
        texts += [a["title"], a["text"]]
    for ld in HEI["lordsdays"]:
        for q in ld["questions"]:
            texts += [q["question"], q["answer"]]
    for h in DOR["heads"]:
        for a in h["articles"]:
            texts += [a["title"], split_dort(a["text"])[0]]
    big = []
    for t in texts:
        t = re.sub(r"\s+", "", MARK.sub("", t))
        big.append(t)
    S = set()
    for t in big:
        for i in range(len(t) - n + 1):
            S.add(t[i:i + n])
    return S


def leak_scan(page, outside, S, n=14):
    t = re.sub(r"\s+", "", "".join(outside))
    hits = []
    i = 0
    while i <= len(t) - n:
        if t[i:i + n] in S:
            j = i + n
            while j < len(t) and t[j - n + 1:j + 1] in S:
                j += 1
            hits.append(t[i:j])
            i = j
        else:
            i += 1
    return hits


def main():
    S = build_ngrams()
    pages = sorted(ROOT.glob("*.html"))
    leaks_total = 0
    for pg in pages:
        p = P()
        p.feed(pg.read_text("utf-8"))
        for f in p.figs:
            check_fig(pg.name, f)
        for v in p.vs:
            check_vs(pg.name, v)
        check_blobs(pg.name, p.blobs)
        hits = leak_scan(pg.name, p.outside, S)
        # known-safe: none; every hit is reported
        rec(pg.name, "leak-scan", "author text vs corpus (>=14 chars)", not hits, "; ".join(h[:60] for h in hits[:5]))
        leaks_total += len(hits)
    # table
    pages_names = [p.name for p in pages]
    print("%-24s %8s %8s %6s %10s   %s" % ("page", "figures", "short", "blobs", "leak-scan", "result"))
    allok = True
    for pn in pages_names:
        rs = [r for r in results if r[0] == pn]
        nf = sum(1 for r in rs if r[1] == "figure" and not any(x in r[2].split(" ", 1)[1] for x in ["/"]))
        ns = sum(1 for r in rs if r[1] == "short")
        nb = sum(1 for r in rs if r[1] == "blob")
        leak = [r for r in rs if r[1] == "leak-scan"][0]
        fails = [r for r in rs if not r[3]]
        ok = not fails
        allok &= ok
        print("%-24s %8d %8d %6d %10s   %s" % (pn, nf, ns, nb, "PASS" if leak[3] else "FAIL", "PASS" if ok else "FAIL (%d)" % len(fails)))
    fails = [r for r in results if not r[3]]
    for r in fails:
        print("  FAIL %s [%s] %s — %s" % (r[0], r[1], r[2], r[4]))
    tot = len(results)
    print("\nchecks: %d, passed: %d, failed: %d  =>  %s" % (tot, tot - len(fails), len(fails), "ALL PASS" if not fails else "FAILURES"))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
