/* memorize hub: flashcards (Leitner boxes), HC Q74 cloze cards, creed line cards, quizzes. Vanilla JS. */
(function(){
  'use strict';
  var d=document;
  function J(id){var e=d.getElementById(id);if(!e)return null;try{return JSON.parse(e.textContent)}catch(x){console.error('bad json '+id);return null}}
  var store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  var C=J('cards-data')||{}, CREEDS=J('creeds-data')||{}, HC=J('hc74-data')||{sentences:[]};
  function el(tag,cls,txt){var e=d.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
  function sa(str,chars){var out=[],cur='';Array.from(str).forEach(function(ch){cur+=ch;if(chars.indexOf(ch)>-1){out.push(cur);cur=''}});if(cur)out.push(cur);return out}
  function shuffle(a){a=a.slice();for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t}return a}
  function creedLines(id){var t=CREEDS[id].text,out=[];if(id==='athanasian'){(t.replace(/\n+/g,'').match(/\d+\)[\s\S]*?(?=\d{1,2}\)|$)/g)||[]).forEach(function(x){x=x.trim();if(x)out.push(x)})}else{t.split(/\n\s*\n/).forEach(function(p){sa(p.trim(),'；。！').forEach(function(x){x=x.trim();if(x)out.push(x)})})}return out}

  /* ---------- build cards ---------- */
  var cards=[];
  (C.heads||[]).forEach(function(c,i){cards.push({id:'h'+i,deck:'heads',k:c.tag||'四点',front:c.q,back:c.a})});
  (C.texts||[]).forEach(function(c,i){cards.push({id:'t'+i,deck:'texts',k:'经文',front:c.q,back:c.a})});
  (C.concepts||[]).forEach(function(c,i){cards.push({id:'c'+i,deck:'concepts',k:'概念',front:c.q,back:c.a})});
  HC.sentences.forEach(function(s,i){
    var ph=sa(s,'，、；：。'), n=0, front=[], k=0;
    ph.forEach(function(p){var core=p.replace(/[，、；：。]$/,''),tail=p.slice(core.length);if(core.length>=4&&(k%2===1)){front.push({b:core});front.push({t:tail})}else front.push({t:p});k++});
    cards.push({id:'hc'+i,deck:'hc74',k:'HC 问74 答 · 第'+(i+1)+'句（填空）',frontParts:front,back:s});
  });
  Object.keys(CREEDS).forEach(function(id){var L=creedLines(id);for(var i=0;i<L.length-1;i++){cards.push({id:'cr-'+id+'-'+i,deck:'creed',k:CREEDS[id].title+' · 下一句是？',front:L[i],back:L[i+1],big:true})}});

  var box={};try{box=JSON.parse(store.get('zw-lb2')||'{}')}catch(e){}
  var deck='heads', cur=null, last=null;
  var elCard=d.getElementById('fc'), elK=d.getElementById('fc-k'), elQ=d.getElementById('fc-q'), elA=d.getElementById('fc-a'), elBar=d.getElementById('fc-bar'), elStat=d.getElementById('fc-stat');
  function inDeck(){return cards.filter(function(c){return deck==='all'||c.deck===deck})}
  function progress(){var L=inDeck(),m=L.filter(function(c){return (box[c.id]||0)>=3}).length;elBar.style.width=(L.length?100*m/L.length:0)+'%';elStat.textContent='已掌握 '+m+' / '+L.length+'（箱≥3 视为掌握）'}
  function pick(){var L=inDeck();if(!L.length)return null;var min=Math.min.apply(null,L.map(function(c){return box[c.id]||0}));var pool=L.filter(function(c){return (box[c.id]||0)<=min+0&&c!==last});if(!pool.length)pool=L.filter(function(c){return c!==last});if(!pool.length)pool=L;return pool[Math.floor(Math.random()*pool.length)]}
  function showCard(c){
    cur=c;last=c;elCard.classList.remove('flip');
    elK.textContent=c.k;elQ.textContent='';
    if(c.frontParts){c.frontParts.forEach(function(p){if(p.b){var s=el('span','cloze-blank',p.b);elQ.appendChild(s)}else elQ.appendChild(d.createTextNode(p.t))});}else elQ.textContent=c.front;
    elA.textContent=c.back;
    d.getElementById('fc-box').textContent='箱 '+(box[c.id]||0);
    progress();
  }
  function next(){var c=pick();if(c)showCard(c)}
  function grade(g){if(!cur)return;var b=box[cur.id]||0;b=g==='good'?Math.min(5,b+1):g==='hard'?b:0;box[cur.id]=b;store.set('zw-lb2',JSON.stringify(box));next()}
  if(elCard){
    elCard.addEventListener('click',function(e){if(e.target.classList.contains('cloze-blank')){e.target.classList.toggle('open');return}elCard.classList.toggle('flip')});
    elCard.addEventListener('keydown',function(e){if(e.key===' '||e.key==='Enter'){e.preventDefault();elCard.classList.toggle('flip')}});
    [].forEach.call(d.querySelectorAll('[data-deck]'),function(b){b.addEventListener('click',function(){deck=b.getAttribute('data-deck');[].forEach.call(d.querySelectorAll('[data-deck]'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});next()})});
    [].forEach.call(d.querySelectorAll('[data-grade]'),function(b){b.addEventListener('click',function(){grade(b.getAttribute('data-grade'))})});
    var rs=d.getElementById('fc-reset');if(rs)rs.addEventListener('click',function(){if(confirm('清除本机上的闪卡进度？')){box={};store.set('zw-lb2','{}');next()}});
    var sf=d.getElementById('fc-skip');if(sf)sf.addEventListener('click',next);
    next();
  }

  /* ---------- MCQ quiz (author-written) ---------- */
  function mcq(host,qs){
    if(!host||!qs||!qs.length)return;var i=0,score=0,answered=false;
    var qEl=host.querySelector('.q-text'),optEl=host.querySelector('.q-opts'),fb=host.querySelector('.q-fb'),sc=host.querySelector('.q-score'),nx=host.querySelector('.q-next');
    function render(){answered=false;var q=qs[i];qEl.textContent=(i+1)+'/'+qs.length+'　'+q.q;optEl.textContent='';fb.textContent='';fb.className='q-fb';nx.hidden=true;
      shuffle(q.opts.map(function(o,j){return {o:o,j:j}})).forEach(function(x){var b=el('button',null,x.o);b.type='button';b.addEventListener('click',function(){if(answered)return;answered=true;var ok=x.j===q.a;if(ok)score++;b.className=ok?'good':'bad';fb.textContent=(ok?'✔ 正确。':'✘ 不对。')+(q.why||'');fb.className='q-fb '+(ok?'ok':'no');sc.textContent='得分 '+score+' / '+(i+1);nx.hidden=false;nx.textContent=i<qs.length-1?'下一题':'重新开始'});optEl.appendChild(b)});}
    nx.addEventListener('click',function(){i=(i+1)%qs.length;if(i===0)score=0;sc.textContent='得分 '+score;render()});
    sc.textContent='得分 0';render();
  }
  mcq(d.getElementById('quiz-cov'),C.quiz);

  /* ---------- creed next-line quiz + ordering ---------- */
  var cq=d.getElementById('quiz-creed');
  if(cq&&Object.keys(CREEDS).length){
    var ids=Object.keys(CREEDS),all={};ids.forEach(function(id){all[id]=creedLines(id)});
    var sel=cq.querySelector('select'),qEl=cq.querySelector('.q-text'),optEl=cq.querySelector('.q-opts'),fb=cq.querySelector('.q-fb'),sc=cq.querySelector('.q-score'),nx=cq.querySelector('.q-next'),ordBtn=cq.querySelector('[data-order]');
    var score=0,tot=0,answered=false,kind='next';
    function pool(id){return all[id]}
    function nextQ(){answered=false;fb.textContent='';fb.className='q-fb';nx.hidden=true;optEl.textContent='';var id=sel.value||ids[0],L=pool(id);
      if(kind==='next'){var i=1+Math.floor(Math.random()*(L.length-1));qEl.textContent='《'+CREEDS[id].title+'》下一句是什么？上一句：'+L[i-1];
        var wrong=shuffle(L.filter(function(x,j){return j!==i})).slice(0,3);var opts=shuffle([{o:L[i],ok:true}].concat(wrong.map(function(w){return {o:w,ok:false}})));
        opts.forEach(function(x){var b=el('button',null,x.o);b.type='button';b.style.textAlign='left';b.addEventListener('click',function(){if(answered)return;answered=true;tot++;if(x.ok)score++;b.className=x.ok?'good':'bad';fb.textContent=x.ok?'✔ 正确':'✘ 正确答案：'+L[i];fb.className='q-fb '+(x.ok?'ok':'no');sc.textContent='得分 '+score+' / '+tot;nx.hidden=false});optEl.appendChild(b)});
      }else{var s=Math.floor(Math.random()*Math.max(1,L.length-3));var seq=L.slice(s,s+4);qEl.textContent='《'+CREEDS[id].title+'》把这几句按原顺序点选（点错会重来）：';var order=[],want=seq.slice();
        shuffle(seq).forEach(function(t){var b=el('button',null,t);b.type='button';b.style.textAlign='left';b.addEventListener('click',function(){if(answered)return;if(t===want[order.length]){order.push(t);b.className='good';b.disabled=true;if(order.length===want.length){answered=true;tot++;score++;fb.textContent='✔ 全部正确';fb.className='q-fb ok';sc.textContent='得分 '+score+' / '+tot;nx.hidden=false}}else{tot++;fb.textContent='✘ 顺序不对，已重置本题';fb.className='q-fb no';sc.textContent='得分 '+score+' / '+tot;order=[];[].forEach.call(optEl.children,function(x){x.className='';x.disabled=false})}});optEl.appendChild(b)});}
    }
    nx.addEventListener('click',nextQ);sel.addEventListener('change',nextQ);
    [].forEach.call(cq.querySelectorAll('[data-kind]'),function(b){b.addEventListener('click',function(){kind=b.getAttribute('data-kind');[].forEach.call(cq.querySelectorAll('[data-kind]'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});nextQ()})});
    sc.textContent='得分 0 / 0';nextQ();
  }
})();
