(function(){
  const data=window.SPORT_DATA, official=window.SPORT_OFFICIAL;
  if(!data)return;
  const normalize=s=>(s||'').toString().toLowerCase().replace(/\s+/g,'').replace(/[－—–]/g,'-');
  const esc=s=>String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
  const mapped=data.products.map(p=>({...p,_type:'mapped',_search:normalize([p.name,p.category,p.barcode||'',...(p.aliases||[])].join(''))}));
  const officialRows=[];
  if(official){
    Object.entries(official).forEach(([key,store])=>{
      const meta=data.stores[key]; if(!meta)return;
      const seen=new Set();
      (store.categories||[]).forEach((cat,idx)=>{
        if(store.mode==='category_rules'){
          officialRows.push({name:cat.name,category:`${meta.name} · 官方可兌換類別`,href:`/${meta.slug}/#cat-${idx+1}`,_search:normalize([cat.name,cat.examples||'',meta.name].join(''))});
        }else{
          (cat.items||[]).forEach(item=>{
            const id=key+'|'+item;
            if(seen.has(id))return; seen.add(id);
            officialRows.push({name:item,category:`${meta.name} · ${cat.name}`,href:`/${meta.slug}/#cat-${idx+1}`,_search:normalize([item,cat.name,meta.name].join(''))});
          });
        }
      });
      (store.bonusCategories||[]).forEach((cat,idx)=>{
        (cat.items||[]).forEach(item=>{
          const id=key+'|bonus|'+item;
          if(seen.has(id))return; seen.add(id);
          officialRows.push({name:item,category:`${meta.name} · 商品券超值加碼 · ${cat.name}`,href:`/${meta.slug}/#bonus-${idx+1}`,_search:normalize([item,cat.name,meta.name,'商品券超值加碼'].join(''))});
        });
      });
    });
  }
  document.querySelectorAll('[data-product-search]').forEach(input=>{
    const box=input.parentElement.querySelector('[data-search-results]');
    input.addEventListener('input',()=>{
      const q=normalize(input.value);if(!q){box.innerHTML='';return}
      const mappedHits=mapped.filter(p=>p._search.includes(q)).slice(0,6);
      const used=new Set(mappedHits.map(p=>normalize(p.name)));
      const officialHits=officialRows.filter(p=>p._search.includes(q)&&!used.has(normalize(p.name))).slice(0,10-mappedHits.length);
      const hits=[
        ...mappedHits.map(p=>({name:p.name,category:p.category,href:p.barcode?`/lookup/?barcode=${encodeURIComponent(p.barcode)}`:`/product/${p.id}/`,tag:p.barcode||'快速查詢'})),
        ...officialHits.map(p=>({...p,tag:'官方清單'}))
      ];
      box.innerHTML=hits.length?hits.map(p=>`<a class="search-row" href="${p.href}"><span><b>${esc(p.name)}</b><small>${esc(p.category)}</small></span><em>${esc(p.tag)}</em></a>`).join(''):'<div class="search-row"><span><b>目前沒找到</b><small>不代表不能兌換，請以官方最新清單為準。</small></span></div>';
    });
  });
})();