(function(){
  const data=window.SPORT_DATA,official=window.SPORT_OFFICIAL,barcodeDb=window.SPORT_BARCODES;
  if(!data)return;
  const params=new URLSearchParams(location.search);
  const barcode=(params.get('barcode')||'').replace(/\D/g,'');
  const root=document.querySelector('[data-lookup-root]');
  const stores=data.stores;
  const statusText={exact:['✓','可兌換','官方清單有相符品項','yes'],category:['✓','可兌換（依官方品類）','符合官方開放類別','category'],unknown:['?','尚未確認','目前沒有足夠資料確認，不代表不能兌換','unknown']};

  function esc(s){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]))}
  function uniq(arr){return [...new Set(arr)]}
  function candidates(code){
    const out=[code];
    if(code.length===12)out.push('0'+code);
    if(code.length===13&&code.startsWith('0'))out.push(code.slice(1));
    return uniq(out.filter(Boolean));
  }
  function fold(s){return (s||'').toString().normalize('NFKC').toLowerCase()}
  function sizeOf(s){
    const t=fold(s);const nums=[...t.matchAll(/(\d{2,4})(?:\s*(?:ml|cc|g))?/g)].map(m=>Number(m[1])).filter(n=>n>=100&&n<=6000);
    return nums.length?nums[nums.length-1]:null;
  }
  function baseName(s){
    return fold(s)
      .replace(/pet|can|nbc/g,'').replace(/pe(?=\d)/g,'')
      .replace(/毫升|公克|公升|ml|cc|kg|g|l/g,'')
      .replace(/\d+(?:\.\d+)?%?/g,'')
      .replace(/[\s\-_/\\|·•・,，.。:：;；'"`~!！?？()（）\[\]【】{}<>《》]+/g,'');
  }
  function similarity(a,b){
    const x=baseName(a),y=baseName(b);if(!x||!y)return 0;
    if(x===y)return 1;
    if(x.includes(y)||y.includes(x))return .96;
    const A=new Set([...x]),B=new Set([...y]);let inter=0;A.forEach(c=>{if(B.has(c))inter++});
    return (2*inter)/(A.size+B.size);
  }
  function sizeCompatible(a,b){
    const x=sizeOf(a),y=sizeOf(b);if(x==null||y==null)return true;
    return Math.abs(x-y)<=1;
  }
  function fixedMatches(record,store){
    if(!store||store.mode==='category_rules')return [];
    const scored=[];
    const groups=[...(store.categories||[]),...(store.bonusCategories||[])];
    groups.forEach(cat=>(cat.items||[]).forEach(item=>{
      if(!sizeCompatible(record.name,item))return;
      const score=similarity(record.name,item);
      if(score>=.88)scored.push({item,score});
    }));
    if(!scored.length)return [];
    scored.sort((a,b)=>b.score-a.score);
    const best=scored[0].score;
    return uniq(scored.filter(x=>x.score>=Math.max(.88,best-.03)).map(x=>x.item));
  }
  function findCategory(storeKey,record){
    const store=official?.[storeKey];if(!store||store.mode!=='category_rules')return null;
    const cats=store.categories||[];const find=(fn)=>cats.find(c=>fn(fold(c.name)))?.name||null;
    if(record.category==='運動飲料')return find(n=>n.includes('運動飲料'));
    if(record.category==='鮮乳')return find(n=>n.includes('冷藏鮮乳')||n.includes('鮮乳、豆奶'));
    if(record.category==='豆漿／穀物飲')return find(n=>n.includes('豆漿')||n.includes('鮮乳、豆奶'));
    if(record.category==='無糖茶')return find(n=>n.includes('無糖茶'));
    if(record.category==='瓶裝水')return find(n=>n.includes('瓶裝水'));
    if(record.category==='優格／優酪乳／發酵乳'){
      if(storeKey==='pxmart'){
        const n=fold(record.name);
        if(n.includes('希臘')&&(n.includes('無糖')||n.includes('無加糖')))return find(x=>x.includes('希臘'));
        if(n.includes('優格')&&(n.includes('無糖')||n.includes('無加糖')))return find(x=>x.includes('無糖優格'));
        if(n.includes('優酪乳')&&(n.includes('無糖')||n.includes('無加糖')))return find(x=>x.includes('無糖優酪乳'));
        return null;
      }
      return find(n=>n.includes('發酵製品'));
    }
    if(record.category==='咖啡'){
      const n=fold(record.name);if(!(n.includes('無糖')||n.includes('黑咖啡')||n.includes('純黑')))return null;
      return find(x=>x.includes('無糖咖啡'));
    }
    return null;
  }
  function resolveRecord(record){
    const out={};
    Object.keys(stores).forEach(k=>{
      const store=official?.[k];
      if(store?.mode==='category_rules'){
        const cat=findCategory(k,record);out[k]=cat?{status:'category',items:[cat]}:{status:'unknown',items:[]};
      }else{
        const items=fixedMatches(record,store);out[k]=items.length?{status:'exact',items}:{status:'unknown',items:[]};
      }
    });
    return out;
  }
  function storeRows(resolved){
    return Object.entries(stores).map(([k,s])=>{
      const rec=resolved[k]||{status:'unknown',items:[]};const st=statusText[rec.status]||statusText.unknown;
      const chips=rec.items?.length?`<div class="item-list">${uniq(rec.items).map(i=>`<span class="item-chip">${esc(i)}</span>`).join('')}</div>`:'';
      return `<div class="store-result"><span class="status ${st[3]}">${st[0]}</span><div class="store-answer"><div class="store-heading"><h3>${esc(s.name)}</h3><span class="status-label">${st[1]}</span></div><small>${st[2]}</small>${chips}<div class="source-note">資料來源：<a class="source" href="${esc(s.source)}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div></div></div>`;
    }).join('');
  }
  function renderResolved(name,category,code,resolved){
    const eligible=Object.values(resolved).filter(s=>s.status==='exact'||s.status==='category').length;
    root.innerHTML=`<div class="receipt"><div class="receipt-top"><div><span class="stamp">${eligible?'找到可兌換資訊 ✓':'已辨識商品'}</span><h1>${esc(name)}</h1><div class="receipt-meta">${esc(category||'商品')}${code?' · '+esc(code):''}</div></div><b>${eligible} 個通路可確認</b></div><div class="store-results">${storeRows(resolved)}</div></div><div class="disclaimer"><strong>提醒</strong><br>門市供應與實際結帳結果仍以官方公告與現場 POS 為準。</div>`;
  }
  function renderProduct(p){renderResolved(p.name,p.category,p.barcode,p.stores||{})}
  function renderBarcodeRecord(record){renderResolved(record.name,record.category,barcode,resolveRecord(record))}
  function renderUnknown(){
    root.innerHTML=`<div class="receipt"><div class="receipt-top"><div><span class="stamp" style="background:#dad8cf">目前找不到</span><h1>這個條碼還沒有商品資料</h1><div class="receipt-meta">${esc(barcode||'未提供條碼')}</div></div></div><p class="lead" style="font-size:15px;margin-top:18px">這不代表不能換。可以直接用商品名稱搜尋官方清單。</p><form action="/" method="get" style="margin-top:16px"><div class="search-wrap"><input class="search-input" name="q" type="search" autocomplete="off" placeholder="輸入商品名稱，例如 原萃、舒跑、鮮乳"><button class="primary" style="margin-top:10px;width:100%">搜尋商品</button></div></form></div>`;
  }

  const codes=candidates(barcode);
  const mapped=(data.products||[]).find(x=>x.barcode&&codes.includes(x.barcode));
  if(mapped){renderProduct(mapped);return}
  const record=(barcodeDb?.items||[]).find(x=>codes.includes(x.barcode));
  if(record){renderBarcodeRecord(record);return}
  renderUnknown();
})();
