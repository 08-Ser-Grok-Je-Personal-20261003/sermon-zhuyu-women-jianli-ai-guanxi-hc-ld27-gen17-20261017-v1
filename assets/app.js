/* shared behaviour: themes, nav, TOC, progress, reveal, tabs. Vanilla JS, no deps. */
(function(){
  'use strict';
  var d=document, root=d.documentElement, body=d.body;
  root.classList.add('js');
  var store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* theme: parchment -> light -> dark */
  var themes=['parchment','light','dark'], names={parchment:'羊皮纸',light:'亮色',dark:'暗色'};
  function setTheme(t){root.setAttribute('data-theme',t);store.set('zw-theme',t);var b=d.getElementById('theme-btn');if(b){var l=b.querySelector('.lbl');if(l)l.textContent=names[t];b.setAttribute('aria-label','切换主题（当前：'+names[t]+'）');}}
  var tb=d.getElementById('theme-btn');
  setTheme(root.getAttribute('data-theme')||'parchment');
  if(tb)tb.addEventListener('click',function(){var i=themes.indexOf(root.getAttribute('data-theme'));setTheme(themes[(i+1)%themes.length]);});

  /* mobile nav */
  var nb=d.getElementById('nav-btn');
  if(nb)nb.addEventListener('click',function(){var o=body.classList.toggle('nav-open');nb.setAttribute('aria-expanded',o?'true':'false');});
  d.addEventListener('click',function(e){if(body.classList.contains('nav-open')&&!e.target.closest('.nav')&&!e.target.closest('#nav-btn')){body.classList.remove('nav-open');if(nb)nb.setAttribute('aria-expanded','false');}});

  /* TOC */
  var toc=d.getElementById('toc'), tbtn=d.getElementById('toc-btn');
  if(toc){
    var wide=function(){return window.matchMedia('(min-width:1100px)').matches};
    var pref=store.get('zw-toc');
    function setToc(open,save){body.setAttribute('data-toc',open?'open':'closed');if(tbtn){tbtn.setAttribute('aria-expanded',open?'true':'false');var l=tbtn.querySelector('.lbl');if(l)l.textContent=open?'隐藏目录':'显示目录';}if(save&&wide())store.set('zw-toc',open?'open':'closed');}
    setToc(wide()?(pref!=='closed'):false,false);
    if(tbtn)tbtn.addEventListener('click',function(){setToc(body.getAttribute('data-toc')!=='open',true);});
    var sc=d.querySelector('.toc-scrim');if(sc)sc.addEventListener('click',function(){setToc(false,false)});
    var cl=toc.querySelector('.toc-close');if(cl)cl.addEventListener('click',function(){setToc(false,true)});
    toc.addEventListener('click',function(e){if(e.target.closest('a')&&!wide())setToc(false,false)});
    d.addEventListener('keydown',function(e){if(e.key==='Escape'){if(!wide())setToc(false,false);body.classList.remove('nav-open')}});
    var links=[].slice.call(toc.querySelectorAll('a[href^="#"]')), map={};
    links.forEach(function(a){var id=decodeURIComponent(a.getAttribute('href').slice(1));var el=d.getElementById(id);if(el)map[id]={a:a,el:el}});
    var ids=Object.keys(map);
    function spy(){var y=window.scrollY+90,cur=null;for(var i=0;i<ids.length;i++){if(map[ids[i]].el.getBoundingClientRect().top+window.scrollY<=y)cur=ids[i];else break;}
      links.forEach(function(a){a.classList.remove('on')});
      if(cur){var a=map[cur].a;a.classList.add('on');if(body.getAttribute('data-toc')==='open'){var r=a.getBoundingClientRect(),tr=toc.getBoundingClientRect();if(r.top<tr.top+40||r.bottom>tr.bottom-40)toc.scrollTop+=r.top-tr.top-tr.height/3;}}}
    var tk=false;window.addEventListener('scroll',function(){if(!tk){tk=true;requestAnimationFrame(function(){spy();tk=false})}},{passive:true});spy();
  }

  /* progress + back to top */
  var pg=d.getElementById('progress'), tt=d.getElementById('totop'), tick=false;
  function onScroll(){var h=root.scrollHeight-window.innerHeight;var p=h>0?Math.min(1,window.scrollY/h):0;if(pg)pg.style.transform='scaleX('+p+')';if(tt)tt.classList.toggle('show',window.scrollY>700);}
  window.addEventListener('scroll',function(){if(!tick){tick=true;requestAnimationFrame(function(){onScroll();tick=false})}},{passive:true});onScroll();
  if(tt)tt.addEventListener('click',function(){window.scrollTo({top:0,behavior:reduce?'auto':'smooth'})});

  /* reveal on scroll */
  var rv=[].slice.call(d.querySelectorAll('.rv'));
  if('IntersectionObserver' in window&&!reduce){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{rootMargin:'0px 0px -6% 0px',threshold:.04});rv.forEach(function(el){io.observe(el)});setTimeout(function(){rv.forEach(function(el){el.classList.add('in')})},4000);}else{rv.forEach(function(el){el.classList.add('in')})}
  /* anchors targeted directly must be visible */
  if(location.hash){var t=d.getElementById(decodeURIComponent(location.hash.slice(1)));if(t){var rr=t.closest('.rv');if(rr)rr.classList.add('in');var dd=t.closest('details');if(dd)dd.open=true;}}

  /* tabs */
  [].forEach.call(d.querySelectorAll('[data-tabs]'),function(box){
    var btns=[].slice.call(box.querySelectorAll('.tab-list button')), panels=[].slice.call(box.querySelectorAll('.tab-panel'));
    function show(i){btns.forEach(function(b,j){b.setAttribute('aria-selected',j===i?'true':'false')});panels.forEach(function(p,j){p.classList.toggle('on',j===i)});}
    btns.forEach(function(b,i){b.addEventListener('click',function(){show(i)});b.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){btns[(i+1)%btns.length].focus();show((i+1)%btns.length)}if(e.key==='ArrowLeft'){btns[(i+btns.length-1)%btns.length].focus();show((i+btns.length-1)%btns.length)}})});
    show(0);
  });
  /* expand/collapse all details inside a container */
  [].forEach.call(d.querySelectorAll('[data-expand]'),function(b){b.addEventListener('click',function(){var open=b.getAttribute('data-expand')==='open';[].forEach.call(d.querySelectorAll(b.getAttribute('data-target')||'details.dq'),function(x){x.open=open})})});
  /* print button */
  [].forEach.call(d.querySelectorAll('[data-print]'),function(b){b.addEventListener('click',function(){window.print()})});
})();
