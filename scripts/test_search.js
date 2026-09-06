const fs=require('fs');
const path=require('path');
const core=require('../public/assets/search-core.js');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/catalog.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'data/official-catalog.json'),'utf8'));
const manual=JSON.parse(fs.readFileSync(path.join(root,'data/manual-lookups.json'),'utf8'));
const official={};
for(const [k,rel] of Object.entries(manifest.stores))official[k]=JSON.parse(fs.readFileSync(path.join(root,rel),'utf8'));
const index=core.buildIndex(data,official,manual);
const failures=[];
let officialRowsTested=0, categoryRulesTested=0;
for(const [storeKey,store] of Object.entries(official)){
  if(store.mode==='category_rules'){
    for(const cat of store.categories){
      categoryRulesTested++;
      const hits=core.search(index,cat.name);
      if(!hits.some(h=>h.type==='official-rule'&&h.storeKey===storeKey&&h.name===cat.name))failures.push(`category search miss: ${storeKey} / ${cat.name}`);
    }
    continue;
  }
  const cats=[...(store.categories||[]),...(store.bonusCategories||[])];
  for(const cat of cats){
    for(const item of cat.items||[]){
      officialRowsTested++;
      const hits=core.search(index,item);
      if(!hits.some(h=>h.type==='official-item'&&h.storeKey===storeKey&&h.name===item))failures.push(`official item search miss: ${storeKey} / ${cat.name} / ${item}`);
    }
  }
}
const variants=[
  ['FMC天然水610ml','family','ＦＭＣ天然水６１０ｍｌ'],
  ['ASAHI十六茶','family','ＡＳＡＨＩ十六茶'],
  ['FIN 580ml','family','ＦＩＮ補給飲料５８０ｍｌ'],
  ['大冰單品美式(安提瓜)','family','大冰單品美式（安提瓜）'],
  ['御茶園四季春1.25L','family','御茶園台灣四季春１．２５Ｌ'],
  ['寶礦力 ion water','family','寶礦力水得ｉｏｎｗａｔｅｒ'],
  ['光泉黑豆漿400ml','hilife','光泉無加糖黑豆漿400ML'],
  ['統一UNI water 550','seven','統一UNI water純水PET550']
];
for(const [q,storeKey,target] of variants){
  const hits=core.search(index,q);
  if(!hits.some(h=>h.storeKey===storeKey&&h.name===target))failures.push(`variant search miss: ${q} -> ${storeKey}/${target}`);
}
for(const item of manual.lookups){
  const hits=core.search(index,item.name);
  if(!hits.some(h=>h.type==='manual'&&h.href===`/product/${item.id}/`))failures.push(`manual search miss: ${item.name}`);
}
const report={officialRowsTested,categoryRulesTested,variantCases:variants.length,manualLookups:manual.lookups.length,failures,pass:failures.length===0};
fs.writeFileSync(path.join(root,'public/search-qa.json'),JSON.stringify(report,null,2));
console.log('SEARCH QA',JSON.stringify(report));
if(failures.length){console.error(failures.join('\n'));process.exit(1)}
