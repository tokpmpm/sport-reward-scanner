(function(){
  const data=window.SPORT_DATA, official=window.SPORT_OFFICIAL, manual=window.SPORT_MANUAL, engine=window.SPORT_SEARCH;
  if(!data||!engine)return;
  const index=engine.buildIndex(data,official,manual);
  const esc=s=>String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
  const state=new WeakMap();
  function render(input,showAll=false){
    const box=input.parentElement.querySelector('[data-search-results]');
    const q=input.value.trim();
    if(!q){box.innerHTML='';state.delete(input);return}
    const hits=engine.search(index,q);
    state.set(input,{q,hits});
    const shown=showAll?hits:hits.slice(0,10);
    const rows=shown.map(p=>`<a class="search-row" href="${p.href}"><span><b>${esc(p.name)}</b><small>${esc(p.category)}</small></span><em>${esc(p.tag||'')}</em></a>`).join('');
    if(!hits.length){
      box.innerHTML='<div class="search-row"><span><b>目前沒找到</b><small>這不代表不能兌換；可改用較短的品牌、商品名或查看完整通路清單。</small></span></div>';
      return;
    }
    const more=!showAll&&hits.length>10?`<button class="search-more" type="button" data-search-more>查看全部 ${hits.length} 筆</button>`:'';
    const collapse=showAll&&hits.length>10?'<button class="search-more" type="button" data-search-less>收合搜尋結果</button>':'';
    box.innerHTML=`<div class="search-count">找到 ${hits.length} 筆 · 依相關度排序</div>${rows}${more}${collapse}`;
  }
  document.querySelectorAll('[data-product-search]').forEach(input=>{
    input.addEventListener('input',()=>render(input,false));
    const box=input.parentElement.querySelector('[data-search-results]');
    box.addEventListener('click',ev=>{
      if(ev.target.closest('[data-search-more]')){ev.preventDefault();render(input,true)}
      if(ev.target.closest('[data-search-less]')){ev.preventDefault();render(input,false);input.scrollIntoView({block:'center'})}
    });
  });
})();
