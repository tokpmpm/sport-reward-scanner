(function(){
  const section=document.querySelector('[data-recommendations]');
  if(!section)return;
  const filters=[...section.querySelectorAll('[data-recommendation-filter]')];
  const cards=[...section.querySelectorAll('[data-recommendation-card]')];
  const empty=section.querySelector('[data-recommendation-empty]');
  let viewed=false;
  const viewedItems=new Set();

  function track(name,params){
    if(typeof window.sportTrack==='function')window.sportTrack(name,params||{});
    else if(typeof window.gtag==='function')window.gtag('event',name,params||{});
  }

  function itemParams(card){
    return {
      recommendation_id:card.dataset.id||'',
      store_name:card.dataset.storeName||'',
      product_name:card.dataset.title||'',
      extra_pay:Number(card.dataset.extra||0),
      has_photo:card.dataset.hasPhoto==='1'
    };
  }

  function applyFilter(value){
    let shown=0;
    cards.forEach(card=>{
      const visible=value==='all'||card.dataset.store===value;
      card.hidden=!visible;
      if(visible)shown++;
    });
    filters.forEach(btn=>btn.setAttribute('aria-pressed',String(btn.dataset.recommendationFilter===value)));
    empty?.classList.toggle('show',shown===0);
    return shown;
  }

  filters.forEach(btn=>btn.addEventListener('click',()=>{
    const value=btn.dataset.recommendationFilter||'all';
    const shown=applyFilter(value);
    track('recommendation_filter',{store_filter:value,result_count:shown});
  }));

  section.addEventListener('click',ev=>{
    const link=ev.target.closest('[data-recommendation-link]');
    if(!link)return;
    const card=link.closest('[data-recommendation-card]');
    if(!card)return;
    track('recommendation_click',{...itemParams(card),link_url:link.href});
  });

  if('IntersectionObserver' in window){
    const sectionObserver=new IntersectionObserver(entries=>{
      if(viewed)return;
      if(entries.some(x=>x.isIntersecting)){
        viewed=true;
        track('recommendation_view',{item_count:cards.length});
        sectionObserver.disconnect();
      }
    },{threshold:.2});
    sectionObserver.observe(section);

    const itemObserver=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(!entry.isIntersecting)return;
        const card=entry.target;
        const id=card.dataset.id||'';
        if(!id||viewedItems.has(id))return;
        viewedItems.add(id);
        track('recommendation_item_view',itemParams(card));
        itemObserver.unobserve(card);
      });
    },{threshold:.5});
    cards.forEach(card=>itemObserver.observe(card));
  }else{
    viewed=true;
    track('recommendation_view',{item_count:cards.length});
    cards.forEach(card=>track('recommendation_item_view',itemParams(card)));
  }
})();
