(function(){
  const section=document.querySelector('[data-recommendations]');
  if(!section)return;
  const filters=[...section.querySelectorAll('[data-recommendation-filter]')];
  const cards=[...section.querySelectorAll('[data-recommendation-card]')];
  const empty=section.querySelector('[data-recommendation-empty]');
  let viewed=false;

  function track(name,params){
    if(typeof window.sportTrack==='function')window.sportTrack(name,params||{});
    else if(typeof window.gtag==='function')window.gtag('event',name,params||{});
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
    track('recommendation_click',{
      recommendation_id:card.dataset.id||'',
      store_name:card.dataset.storeName||'',
      product_name:card.dataset.title||'',
      extra_pay:Number(card.dataset.extra||0),
      link_url:link.href
    });
  });

  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      if(viewed)return;
      if(entries.some(x=>x.isIntersecting)){
        viewed=true;
        track('recommendation_view',{item_count:cards.length});
        observer.disconnect();
      }
    },{threshold:.2});
    observer.observe(section);
  }else{
    viewed=true;
    track('recommendation_view',{item_count:cards.length});
  }
})();
