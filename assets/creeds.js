/* creed reader: font size, line numbers, cloze, progressive reveal, self-test.
   All practice text is derived at runtime from the verbatim creed text already present in the page (.creed-text). */
(function(){
  'use strict';
  var d=document, store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  var reader=d.getElementById('reader'); if(!reader)return;
  var secs=[].slice.call(d.querySelectorAll('.creed-sec'));
  var mode='read', cfg={gran:'phrase',n:3,seed:0};
  /* font size + line numbers */
  var fs=d.getElementById('fs'), fsv=d.getElementById('fs-val');
  function setFs(v){reader.style.setProperty('--fs',v+'rem');if(fsv)fsv.textContent=Math.round(v*100)+'%';store.set('zw-fs',v)}
  if(fs){var sv=parseFloat(store.get('zw-fs'))||1.35;fs.value=sv;setFs(sv);fs.addEventListener('input',function(){setFs(parseFloat(fs.value))});}
  var lnb=d.getElementById('ln-btn');
  if(lnb)lnb.addEventListener('click',function(){var on=reader.classList.toggle('ln-on');lnb.setAttribute('aria-pressed',on?'true':'false')});
  /* theme segment mirrors site theme */
  [].forEach.call(d.querySelectorAll('[data-settheme]'),function(b){b.addEventListener('click',function(){document.documentElement.setAttribute('data-theme',b.getAttribute('data-settheme'));try{localStorage.setItem('zw-theme',b.getAttribute('data-settheme'))}catch(e){}})});

  function sa(str,chars){var out=[],cur='';Array.from(str).forEach(function(ch){cur+=ch;if(chars.indexOf(ch)>-1){out.push(cur);cur=''}});if(cur)out.push(cur);return out}
  function lineSplit(sec){
    var id=sec.getAttribute('data-creed'), box=sec.querySelector('.creed-text');
    var paras=[].map.call(box.querySelectorAll('p'),function(p){return p.textContent.trim()});
    var lines=[];
    if(id==='athanasian'){(paras.join('').match(/\d+\)[\s\S]*?(?=\d{1,2}\)|$)/g)||[]).forEach(function(x){x=x.trim();if(x)lines.push(x)});}
    else{paras.forEach(function(p){sa(p,'；。！').forEach(function(x){x=x.trim();if(x)lines.push(x)})});}
    return lines;
  }
  var data=secs.map(function(s){return {sec:s,id:s.getAttribute('data-creed'),lines:lineSplit(s),k:0,prac:s.querySelector('.practice'),read:s.querySelector('.vq')}});
  var PUNCT=/[，、；：。！？“”‘’（）()·\s]/, NUM=/^\d+\)$/;

  function el(tag,cls,txt){var e=d.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
  function blank(text){var s=el('span','cloze-blank',text);s.tabIndex=0;s.setAttribute('role','button');s.setAttribute('aria-label','点击显示');var t=function(){s.classList.toggle('open')};s.addEventListener('click',t);s.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();t()}});return s}

  function renderCloze(D){
    var p=D.prac;p.textContent='';var n=cfg.n,c=0;
    D.lines.forEach(function(line,li){
      var row=el('div','pl');
      if(cfg.gran==='line'){
        if((li+cfg.seed)%n===n-1){row.className='pl hid';row.textContent=line;row.tabIndex=0;var t=function(){row.classList.toggle('open')};row.addEventListener('click',t);row.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();t()}});}
        else row.textContent=line;
      }else if(cfg.gran==='phrase'){
        sa(line,'，、；：。！？').forEach(function(ph){
          var core=ph.replace(/[，、；：。！？]$/,''),tail=ph.slice(core.length);
          if(core&&!NUM.test(core.trim())&&(c+cfg.seed)%n===n-1){var m=core.match(/^(\d+\)\s*)(.*)$/);if(m&&m[2]){row.appendChild(d.createTextNode(m[1]));row.appendChild(blank(m[2]))}else row.appendChild(blank(core));row.appendChild(d.createTextNode(tail))}
          else row.appendChild(d.createTextNode(ph));
          c++;
        });
      }else{
        var chars=Array.from(line),i=0;
        var m0=line.match(/^\d+\)\s*/);if(m0){row.appendChild(d.createTextNode(m0[0]));chars=Array.from(line.slice(m0[0].length))}
        chars.forEach(function(ch){if(PUNCT.test(ch)){row.appendChild(d.createTextNode(ch))}else{if((c+cfg.seed)%n===n-1)row.appendChild(blank(ch));else row.appendChild(d.createTextNode(ch));c++}});
      }
      p.appendChild(row);
    });
  }
  function renderProg(D){
    var p=D.prac;p.textContent='';
    D.lines.forEach(function(line,i){var row=el('div','pl',line);if(i>D.k)row.className='pl future';else if(i===D.k&&D.k>0&&false){}p.appendChild(row)});
    var nx=D.lines[D.k+1];
    if(nx!==undefined){var h=el('div','pl hid');h.textContent=nx;h.tabIndex=0;h.addEventListener('click',function(){D.k++;renderProg(D)});h.title='点击显示下一句';p.insertBefore(h,p.children[D.k+1]);}
    var info=el('div','muted small','已显示 '+(D.k+1)+' / '+D.lines.length+' 句 · 先在心里背出灰色的下一句，再点击核对');
    info.style.fontFamily='var(--sans)';p.appendChild(info);
    var ctrl=el('div','ctrl');
    [['上一句',function(){if(D.k>0)D.k--;renderProg(D)}],['下一句',function(){if(D.k<D.lines.length-1)D.k++;renderProg(D)}],['全部显示',function(){D.k=D.lines.length-1;renderProg(D)}],['重置',function(){D.k=0;renderProg(D)}]].forEach(function(b){var x=el('button',null,b[0]);x.type='button';x.addEventListener('click',b[1]);ctrl.appendChild(x)});
    p.appendChild(ctrl);
  }
  function normTxt(s){return s.replace(/^\d+\)\s*/,'').replace(/[，、；：。！？“”‘’（）()·\s]/g,'')}
  function renderTest(D){
    var p=D.prac;p.textContent='';
    var idx=D.t==null?Math.floor(Math.random()*D.lines.length):D.t;D.t=idx;
    var prompt=idx>0?D.lines[idx-1]:'（本信经的第一句）';
    var h=el('div','muted small','自测：根据上一句，默写下一句（忽略标点与空格）。第 '+(idx+1)+' / '+D.lines.length+' 句');h.style.fontFamily='var(--sans)';p.appendChild(h);
    p.appendChild(el('div','pl',prompt));
    var row=el('div','pl');var inp=el('input');inp.type='text';inp.placeholder='在此默写…';inp.setAttribute('aria-label','默写');row.appendChild(inp);p.appendChild(row);
    var res=el('div','pl');res.style.display='none';p.appendChild(res);
    var ctrl=el('div','ctrl');
    var chk=el('button','pri','检查');chk.type='button';var nxt=el('button',null,'换一句');nxt.type='button';var show=el('button',null,'看答案');show.type='button';
    chk.addEventListener('click',function(){var ok=normTxt(inp.value)===normTxt(D.lines[idx]);res.style.display='block';res.className='pl '+(ok?'ok':'no');res.textContent=(ok?'✔ 正确：':'✘ 原文：')+D.lines[idx];D.score=D.score||{ok:0,all:0};D.score.all++;if(ok)D.score.ok++;sc.textContent='得分 '+D.score.ok+' / '+D.score.all});
    show.addEventListener('click',function(){res.style.display='block';res.className='pl';res.textContent='原文：'+D.lines[idx]});
    nxt.addEventListener('click',function(){D.t=null;renderTest(D)});
    inp.addEventListener('keydown',function(e){if(e.key==='Enter')chk.click()});
    ctrl.appendChild(chk);ctrl.appendChild(show);ctrl.appendChild(nxt);var sc=el('span','chip grace',D.score?('得分 '+D.score.ok+' / '+D.score.all):'得分 0 / 0');ctrl.appendChild(sc);p.appendChild(ctrl);
  }
  function apply(){
    data.forEach(function(D){
      if(mode==='read'){D.prac.hidden=true;D.read.hidden=false;return}
      D.read.hidden=true;D.prac.hidden=false;
      if(mode==='cloze')renderCloze(D);else if(mode==='prog')renderProg(D);else renderTest(D);
    });
    [].forEach.call(d.querySelectorAll('[data-cfg]'),function(x){x.hidden=(mode!=='cloze')});
    [].forEach.call(d.querySelectorAll('#modes button'),function(b){b.setAttribute('aria-pressed',b.getAttribute('data-mode')===mode?'true':'false')});
  }
  [].forEach.call(d.querySelectorAll('#modes button'),function(b){b.addEventListener('click',function(){mode=b.getAttribute('data-mode');data.forEach(function(D){D.k=0;D.t=null});apply()})});
  var g=d.getElementById('gran'),nn=d.getElementById('nth'),nv=d.getElementById('nth-val'),rs=d.getElementById('reshuffle');
  if(g)g.addEventListener('change',function(){cfg.gran=g.value;apply()});
  if(nn)nn.addEventListener('input',function(){cfg.n=parseInt(nn.value,10);if(nv)nv.textContent=cfg.n;apply()});
  if(rs)rs.addEventListener('click',function(){cfg.seed=(cfg.seed+1)%cfg.n;apply()});
  var ra=d.getElementById('reveal-all');if(ra)ra.addEventListener('click',function(){[].forEach.call(d.querySelectorAll('.cloze-blank,.pl.hid'),function(x){x.classList.add('open')})});
  var rh=d.getElementById('hide-all');if(rh)rh.addEventListener('click',function(){[].forEach.call(d.querySelectorAll('.cloze-blank,.pl.hid'),function(x){x.classList.remove('open')})});
  [].forEach.call(d.querySelectorAll('[data-themeinit]'),function(){});
  (function(){var cur=document.documentElement.getAttribute('data-theme');[].forEach.call(d.querySelectorAll('[data-settheme]'),function(b){b.setAttribute('aria-pressed',b.getAttribute('data-settheme')===cur?'true':'false')});var mo=new MutationObserver(function(){var t=document.documentElement.getAttribute('data-theme');[].forEach.call(d.querySelectorAll('[data-settheme]'),function(b){b.setAttribute('aria-pressed',b.getAttribute('data-settheme')===t?'true':'false')})});mo.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']})})();
  apply();
})();
