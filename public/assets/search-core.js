(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.SPORT_SEARCH=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  function fold(value){
    return (value||'').toString().normalize('NFKC').toLowerCase()
      .replace(/[－—–―]/g,'-')
      .replace(/[﹒．。]/g,'.')
      .replace(/毫升/g,'ml').replace(/公克/g,'g').replace(/公升/g,'l');
  }
  function compact(value){
    return fold(value).replace(/[\s\-_/\\|·•・,，.。:：;；'"`~!！?？()（）\[\]【】{}<>《》]+/g,'');
  }
  function tokens(value){
    const f=fold(value).trim();
    const parts=f.split(/[\s\-_/\\|·•・,，.。:：;；'"`~!！?？()（）\[\]【】{}<>《》]+/).map(compact).filter(Boolean);
    return parts.length?parts:[compact(f)].filter(Boolean);
  }
  function isSubsequence(needle,haystack){
    if(!needle||!haystack||needle.length>haystack.length)return false;
    let i=0;
    for(let j=0;j<haystack.length&&i<needle.length;j++)if(needle[i]===haystack[j])i++;
    return i===needle.length;
  }
  function uniquePush(arr,seen,obj,key){
    if(seen.has(key))return;seen.add(key);arr.push(obj);
  }
  function buildIndex(data,official,manual){
    const rows=[],seen=new Set();
    (manual?.lookups||[]).forEach(x=>uniquePush(rows,seen,{
      type:'manual',name:x.name,category:'沒有條碼／不好掃，直接找',aliases:x.aliases||[],href:`/product/${x.id}/`,tag:'直接查'
    },`manual|${x.id}`));
    (data?.products||[]).forEach(p=>uniquePush(rows,seen,{
      type:'mapped',name:p.name,category:p.category||'',aliases:[...(p.aliases||[]),p.barcode||''],href:p.barcode?`/lookup/?barcode=${encodeURIComponent(p.barcode)}`:`/product/${p.id}/`,tag:p.barcode||'快速查詢'
    },`mapped|${p.id}`));
    Object.entries(official||{}).forEach(([storeKey,store])=>{
      const meta=data?.stores?.[storeKey];if(!meta)return;
      if(store.mode==='category_rules'){
        (store.categories||[]).forEach((cat,idx)=>uniquePush(rows,seen,{
          type:'official-rule',storeKey,storeName:meta.name,name:cat.name,category:`${meta.name} · 官方可兌換類別`,aliases:[cat.examples||''],href:`/${meta.slug}/#cat-${idx+1}`,tag:'官方類別'
        },`rule|${storeKey}|${cat.name}`));
        return;
      }
      const groups=[...(store.categories||[]).map((c,i)=>({cat:c,idx:i+1,prefix:'cat'})),...(store.bonusCategories||[]).map((c,i)=>({cat:c,idx:i+1,prefix:'bonus'}))];
      groups.forEach(({cat,idx,prefix})=>(cat.items||[]).forEach(item=>uniquePush(rows,seen,{
        type:'official-item',storeKey,storeName:meta.name,name:item,category:`${meta.name} · ${cat.name}`,aliases:[cat.name,meta.name],href:`/${meta.slug}/#${prefix}-${idx}`,tag:'官方清單'
      },`official|${storeKey}|${cat.name}|${item}`)));
    });
    return rows.map((r,index)=>{
      const nameCompact=compact(r.name), aliasCompact=(r.aliases||[]).map(compact).filter(Boolean);
      const hayCompact=compact([r.name,r.category,...(r.aliases||[])].join(' '));
      return {...r,_index:index,_nameCompact:nameCompact,_aliasCompact:aliasCompact,_hayCompact:hayCompact};
    });
  }
  function scoreRow(row,query){
    const q=compact(query);if(!q)return -1;
    const qt=tokens(query);
    const name=row._nameCompact||compact(row.name);
    const hay=row._hayCompact||compact([row.name,row.category,...(row.aliases||[])].join(' '));
    const aliases=row._aliasCompact||(row.aliases||[]).map(compact);
    if(name===q)return 1000;
    if(aliases.some(a=>a===q))return 960;
    if(name.startsWith(q))return 920;
    if(name.includes(q))return 880;
    if(aliases.some(a=>a.includes(q)))return 850;
    if(qt.length>1&&qt.every(t=>hay.includes(t)))return 800;
    if(hay.includes(q))return 760;
    if(q.length>=4&&isSubsequence(q,name))return 700-Math.min(120,name.length-q.length);
    if(q.length>=4&&isSubsequence(q,hay))return 620-Math.min(120,hay.length-q.length);
    return -1;
  }
  function search(index,query){
    return (index||[]).map(row=>({row,score:scoreRow(row,query)})).filter(x=>x.score>=0)
      .sort((a,b)=>b.score-a.score||a.row._index-b.row._index).map(x=>x.row);
  }
  return {fold,compact,tokens,isSubsequence,buildIndex,scoreRow,search};
});
