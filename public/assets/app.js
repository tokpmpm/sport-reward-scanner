(function(){
  const data=window.SPORT_DATA;if(!data)return;
  const normalize=s=>(s||'').toString().toLowerCase().replace(/\s+/g,'').replace(/[－—–]/g,'-');
  const searchable=data.products.map(p=>({...p,_search:normalize([p.name,p.category,p.barcode||'',...(p.aliases||[])].join(''))}));
  function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
  document.querySelectorAll('[data-product-search]').forEach(input=>{
    const box=input.parentElement.querySelector('[data-search-results]');
    input.addEventListener('input',()=>{
      const q=normalize(input.value);if(!q){box.innerHTML='';return}
      const hits=searchable.filter(p=>p._search.includes(q)).slice(0,10);
      box.innerHTML=hits.length?hits.map(p=>{
        const href=p.barcode?`/lookup/?barcode=${encodeURIComponent(p.barcode)}`:`/product/${p.id}/`;
        return `<a class="search-row" href="${href}"><span><b>${esc(p.name)}</b><small>${esc(p.category)}</small></span><em>${p.barcode?esc(p.barcode):'無固定條碼'}</em></a>`
      }).join(''):'<div class="search-row"><span><b>目前沒找到</b><small>不代表不能兌換，請以官方清單為準。</small></span></div>';
    });
  });
})();
