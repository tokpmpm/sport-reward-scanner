(function(){
  const data=window.SPORT_DATA;if(!data)return;
  const params=new URLSearchParams(location.search);const barcode=(params.get('barcode')||'').replace(/\D/g,'');
  const root=document.querySelector('[data-lookup-root]');
  const stores=data.stores;
  const statusText={exact:['✓','可兌換','官方品項明列','yes'],category:['✓','可兌換','符合官方開放品類','category'],unknown:['?','尚未確認','本站目前資料不足','unknown'],no:['×','不適用','官方規則不符','unknown']};
  function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
  function renderProduct(p){
    const eligible=Object.values(p.stores).filter(s=>s.status==='exact'||s.status==='category').length;
    root.innerHTML=`<div class="receipt"><div class="receipt-top"><div><span class="stamp">${eligible?'可以換 ✓':'需要再確認'}</span><h1>${esc(p.name)}</h1><div class="receipt-meta">${esc(p.category)}${p.barcode?' · '+esc(p.barcode):''}</div></div><b>${eligible} 個通路有可兌換品項</b></div><div class="store-results">${Object.entries(stores).map(([k,s])=>{const rec=p.stores[k]||{status:'unknown',items:[]};const st=statusText[rec.status]||statusText.unknown;return `<div class="store-result"><span class="status ${st[3]}">${st[0]}</span><div class="store-answer"><div class="store-heading"><h3>${esc(s.name)}</h3><span class="status-label">${st[1]}</span></div><small>${st[2]}</small>${rec.items?.length?`<div class="item-list">${rec.items.map(i=>`<span class="item-chip">${esc(i)}</span>`).join('')}</div>`:''}<div class="source-note">資料來源：<a class="source" href="${s.source}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div></div></div>`}).join('')}</div></div><div class="disclaimer"><strong>非官方查詢工具</strong><br>資料整理自運動部「揮汗有禮」官方資訊，可能有遺漏或誤植；實際可兌換品項、門市供應及結帳結果請以官方最新公告與門市 POS 為準。</div>`;
  }
  const p=data.products.find(x=>x.barcode===barcode);
  if(p)renderProduct(p);else root.innerHTML=`<div class="receipt"><div class="receipt-top"><div><span class="stamp" style="background:#dad8cf">尚未收錄 ?</span><h1>這個條碼還沒確認</h1><div class="receipt-meta">${esc(barcode||'未提供條碼')}</div></div></div><p class="lead" style="font-size:15px;margin-top:18px">這不代表不能換。本站目前只是還沒有這個條碼資料，請改用商品名稱搜尋或查看官方清單。</p></div><div class="disclaimer"><strong>請不要把「沒收錄」當成「不能換」</strong><br>資料庫會持續補充，官方公告與門市 POS 才是最終依據。</div>`;
})();
