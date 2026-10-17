/* client-side search filter + jump for the Three Forms pages */
(function(){
  'use strict';
  var d=document, input=d.getElementById('q-search'), items=[].slice.call(d.querySelectorAll('.item')), count=d.getElementById('count');
  var cache=null, timer=null;
  function norm(s){return s.toLowerCase().replace(/\s+/g,'')}
  function build(){cache=items.map(function(el){return norm(el.textContent)})}
  function run(){
    var q=norm(input.value||'');
    if(!cache)build();
    var shown=0;
    items.forEach(function(el,i){var ok=!q||cache[i].indexOf(q)>-1;el.hidden=!ok;if(ok)shown++});
    [].forEach.call(d.querySelectorAll('section.sec[id^="h"]'),function(s){var any=s.querySelector('.item:not([hidden])');s.hidden=!any&&!!q;});
    if(count)count.textContent=q?('命中 '+shown+' / '+items.length):('共 '+items.length+' 项');
  }
  if(input){input.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(run,120)});run();}
  var go=d.getElementById('jump-go'), n=d.getElementById('jump-n');
  if(go&&n){var f=function(){var v=parseInt(n.value,10);if(v>=1&&v<=129){if(input){input.value='';run();}location.hash='q'+v;}};go.addEventListener('click',f);n.addEventListener('keydown',function(e){if(e.key==='Enter')f()});}
})();
(function(){
  [].forEach.call(document.querySelectorAll('form[data-goto]'),function(f){f.addEventListener('submit',function(e){e.preventDefault();var v=f.querySelector('input,select').value;if(v)location.href=f.getAttribute('data-goto')+v;});});
})();
