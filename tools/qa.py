#!/usr/bin/env python3
"""Headless-Chrome QA: overflow, TOC toggles, cloze/flashcards, console errors, screenshots.
usage: python3 tools/qa.py [outdir] [--shots]"""
import sys, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path("/workspace/shots-zw-v1")
SHOTS = "--shots" in sys.argv
OUT.mkdir(parents=True, exist_ok=True)
WIDTHS = [(360, 780), (400, 860), (768, 1024), (1280, 800)]
pages = [p.name for p in sorted(ROOT.glob("*.html"))]

JS_OVERFLOW = r"""
() => {
  const W = window.innerWidth, res = {sw: document.documentElement.scrollWidth, bw: document.body.scrollWidth, W, bad: []};
  const inScroll = el => { for (let e = el; e && e !== document.body; e = e.parentElement) {
      if (e.classList && (e.classList.contains('tbl-wrap') || e.classList.contains('svg-wrap') || e.classList.contains('scrollbox'))) return true;
      const cs = getComputedStyle(e); if ((cs.overflowX === 'auto' || cs.overflowX === 'scroll') && e !== document.documentElement) return true; } return false; };
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('svg') && el.tagName.toLowerCase() !== 'svg') continue;
    const r = el.getBoundingClientRect(); if (r.width === 0 && r.height === 0) continue;
    const cs = getComputedStyle(el); if (cs.position === 'fixed' || cs.visibility === 'hidden' || cs.display === 'none') continue;
    if (el.closest('[hidden]') || el.closest('.sr-only') || el.closest('#toc') && getComputedStyle(document.body).getPropertyValue('--x')==='') {}
    if (inScroll(el)) continue;
    if (el.closest('#toc')) continue;
    if (r.right > W + 1 || r.left < -1) res.bad.push(['out', el.tagName + '.' + (el.className && el.className.baseVal === undefined ? el.className : ''), Math.round(r.left), Math.round(r.right)]);
    else if (el.scrollWidth > el.clientWidth + 2 && ['visible','clip'].indexOf(cs.overflowX) < 0 && !inScroll(el.parentElement||el)) res.bad.push(['inner', el.tagName + '.' + el.className + ' «' + (el.textContent||'').slice(0,30) + '»', el.scrollWidth, el.clientWidth]);
  }
  // elements overflowing their card (child wider than card content)
  for (const card of document.querySelectorAll('.card,.co,.vq,.vs,.sitecard,.print-sheet,details.dq,.fc-face')) {
    if (inScroll(card)) continue;
    const cr = card.getBoundingClientRect();
    for (const ch of card.querySelectorAll('*')) {
      if (inScroll(ch) && ch.closest('.tbl-wrap,.svg-wrap')) continue;
      if (ch.closest('svg') && ch.tagName.toLowerCase() !== 'svg') continue;
      const r = ch.getBoundingClientRect(); if (!r.width) continue;
      if (getComputedStyle(ch).position==='absolute') continue;
      if (ch.closest('.tbl-wrap,.svg-wrap')) continue;
      if (r.right > cr.right + 2 || r.left < cr.left - 2) { res.bad.push(['card', card.className + ' > ' + ch.tagName + '.' + (ch.className.baseVal === undefined ? ch.className : ''), Math.round(r.left - cr.left), Math.round(r.right - cr.right)]); break; }
    }
  }
  return res;
}
"""

report = []
def log(page, w, msg):
    report.append((page, w, msg)); print("[%s @%d] %s" % (page, w, msg))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--disable-gpu"])
    for pg in pages:
        for w, h in WIDTHS:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            errs = []
            page.on("console", lambda m, errs=errs: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e, errs=errs: errs.append("PAGEERROR " + str(e)))
            page.on("requestfailed", lambda r, errs=errs: errs.append("REQFAIL " + r.url))
            page.goto((ROOT / pg).as_uri())
            page.wait_for_timeout(400)
            # reveal everything
            page.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
            for th in ("parchment", "dark", "light"):
                page.evaluate("t=>document.documentElement.setAttribute('data-theme',t)", th)
                if th != "parchment" and w != 360:
                    continue
                r = page.evaluate(JS_OVERFLOW)
                ok = r["sw"] <= w and r["bw"] <= w
                if not ok:
                    log(pg, w, "FAIL scrollWidth %s/%s > %s (theme %s)" % (r["sw"], r["bw"], w, th))
                if r["bad"]:
                    log(pg, w, "OVERFLOW %s: %s" % (th, json.dumps(r["bad"][:6], ensure_ascii=False)))
            page.evaluate("document.documentElement.setAttribute('data-theme','parchment')")
            # TOC
            if page.query_selector("#toc-btn"):
                body = lambda: page.evaluate("document.body.getAttribute('data-toc')")
                s0 = body()
                page.click("#toc-btn"); page.wait_for_timeout(350)
                s1 = body()
                vis = page.evaluate("(()=>{const t=document.getElementById('toc');const r=t.getBoundingClientRect();return [r.left,r.right,r.width,innerWidth]})()")
                if s0 == s1:
                    log(pg, w, "FAIL toc toggle no state change %s" % s0)
                elif w < 1100 and s1 == "open" and not (vis[0] >= -1 and vis[1] <= vis[3] + 1):
                    log(pg, w, "FAIL toc drawer not inside viewport %s" % vis)
                if w < 1100 and s1 == "open":
                    r = page.evaluate(JS_OVERFLOW)
                    if r["sw"] > w: log(pg, w, "FAIL drawer open scrollWidth")
                    # close via scrim (click on the uncovered strip) then reopen and close via the drawer's close button
                    page.mouse.click(w - 4, 300); page.wait_for_timeout(350)
                    if body() != "closed": log(pg, w, "FAIL scrim click does not close drawer")
                    page.click("#toc-btn"); page.wait_for_timeout(350)
                    if page.query_selector("#toc .toc-close"):
                        page.click("#toc .toc-close"); page.wait_for_timeout(350)
                        if body() != "closed": log(pg, w, "FAIL close button does not close drawer")
                    # clicking a TOC link closes drawer and navigates
                else:
                    page.click("#toc-btn"); page.wait_for_timeout(350)
                    if body() != s0:
                        log(pg, w, "FAIL toc second toggle %s -> %s -> %s" % (s0, s1, body()))
            # page-specific
            if pg == "creeds-read.html":
                for mode in ("cloze", "prog", "test"):
                    page.click('#modes button[data-mode=%s]' % mode); page.wait_for_timeout(250)
                    n = page.evaluate("document.querySelectorAll('.practice:not([hidden])').length")
                    if n < 1: log(pg, w, "FAIL mode %s shows no practice area" % mode)
                    if mode == "cloze":
                        nb = page.evaluate("document.querySelectorAll('.cloze-blank').length")
                        if nb < 5: log(pg, w, "FAIL cloze blanks=%d" % nb)
                        else:
                            page.evaluate("document.querySelector('.cloze-blank').scrollIntoView({block:'center'})")
                            page.wait_for_timeout(150)
                            page.click('.cloze-blank >> nth=0')
                            op = page.evaluate("document.querySelectorAll('.cloze-blank.open').length")
                            if op < 1: log(pg, w, "FAIL cloze tap doesn't reveal")
                        for sel in ("#gran",):
                            for v in ("char", "line", "phrase"):
                                page.select_option(sel, v); page.wait_for_timeout(100)
                        page.fill("#nth", "2") if False else None
                    r = page.evaluate(JS_OVERFLOW)
                    if r["sw"] > w: log(pg, w, "FAIL overflow in mode %s: %s" % (mode, r["bad"][:4]))
                    if SHOTS and w in (360, 1280):
                        page.screenshot(path=str(OUT / ("creeds-%s-%d.png" % (mode, w))))
                page.click('#modes button[data-mode=read]')
                page.evaluate("var e=document.getElementById('fs');e.value=2;e.dispatchEvent(new Event('input',{bubbles:true}))")
                page.click("#ln-btn"); page.wait_for_timeout(150)
                r = page.evaluate(JS_OVERFLOW)
                if r["sw"] > w: log(pg, w, "FAIL overflow big font + line numbers: %s" % r["bad"][:4])
                if SHOTS and w in (360, 1280): page.screenshot(path=str(OUT / ("creeds-bigfont-%d.png" % w)))
            if pg == "memorize.html":
                for d in ("heads", "texts", "concepts", "hc74", "creed", "all"):
                    page.click('[data-deck=%s]' % d); page.wait_for_timeout(120)
                    q = page.evaluate("document.getElementById('fc-q').textContent.length")
                    if q < 2: log(pg, w, "FAIL deck %s empty" % d)
                    page.click("#fc", position={"x":6,"y":6}); page.wait_for_timeout(700)
                    fl = page.evaluate("document.getElementById('fc').classList.contains('flip')")
                    if not fl: log(pg, w, "FAIL deck %s card did not flip" % d)
                    # card text fits?
                    fit = page.evaluate("(()=>{const out=[];document.querySelectorAll('.fc-face').forEach(f=>{if(f.scrollHeight>f.clientHeight+2)out.push(f.className+' '+f.scrollHeight+'>'+f.clientHeight)});return out})()")
                    if fit: log(pg, w, "WARN card text scrolls inside face (%s): %s" % (d, fit))
                    page.click('[data-grade=good]'); page.wait_for_timeout(100)
                page.click('[data-deck=hc74]'); page.wait_for_timeout(150)
                if SHOTS and w in (360, 1280): page.screenshot(path=str(OUT / ("memorize-card-%d.png" % w)))
                # quizzes
                for host in ("#quiz-cov", "#quiz-creed"):
                    n = page.evaluate("document.querySelectorAll('%s .q-opts button').length" % host)
                    if n < 2: log(pg, w, "FAIL %s no options" % host); continue
                    page.click("%s .q-opts button >> nth=0" % host); page.wait_for_timeout(100)
                    fb = page.evaluate("document.querySelector('%s .q-fb').textContent.length" % host)
                    if fb < 1: log(pg, w, "FAIL %s no feedback" % host)
                if page.query_selector('#quiz-creed [data-kind=order]'):
                    page.click('#quiz-creed [data-kind=order]'); page.wait_for_timeout(150)
                    if page.evaluate("document.querySelectorAll('#quiz-creed .q-opts button').length") < 2: log(pg, w, "FAIL order quiz empty")
            if pg in ("hc.html", "belgic.html", "dort.html"):
                page.fill("#q-search", "拣选" if pg=="dort.html" else "洗礼"); page.wait_for_timeout(400)
                vis = page.evaluate("[...document.querySelectorAll('.item')].filter(e=>!e.hidden && getComputedStyle(e).display!=='none').length")
                tot = page.evaluate("document.querySelectorAll('.item').length")
                if not (0 < vis < tot): log(pg, w, "FAIL search filter visible=%d total=%d" % (vis, tot))
                page.fill("#q-search", "")
            if errs:
                log(pg, w, "CONSOLE ERRORS: %s" % errs[:4])
            if SHOTS:
                page.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
                page.screenshot(path=str(OUT / ("%s-%d.png" % (pg[:-5], w))), full_page=True)
            ctx.close()
    b.close()
print("\nQA done; %d findings" % len(report))
json.dump(report, open(OUT / "report.json", "w"), ensure_ascii=False, indent=1)
