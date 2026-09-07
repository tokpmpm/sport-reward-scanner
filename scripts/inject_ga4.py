import pathlib

# Runs after static generation so every generated HTML page receives the same GA4 tag.
ROOT = pathlib.Path(__file__).resolve().parents[1]
PUB = ROOT / 'public'
MEASUREMENT_ID = 'G-VZ2E4RJMB7'

TAG = f'''<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{MEASUREMENT_ID}');
</script>
<script src="/assets/analytics.js"></script>'''

ANALYTICS_JS = r'''(function(){
  window.sportTrack=function(name,params){
    if(typeof window.gtag==='function') window.gtag('event',name,params||{});
  };

  function text(el){return (el?.textContent||'').trim()}
  function storeNameFromHref(href){
    const map={
      '/7-eleven/':'7-ELEVEN',
      '/familymart/':'全家',
      '/hilife/':'萊爾富',
      '/pxmart/':'全聯',
      '/wanjiafu/':'萬家福／樂家康'
    };
    try{return map[new URL(href,location.href).pathname]||''}catch{return ''}
  }

  document.addEventListener('DOMContentLoaded',function(){
    if(location.pathname==='/scan/'||location.pathname==='/scan'){
      sportTrack('scan_start',{page_path:location.pathname});
    }

    if(location.pathname==='/lookup/'||location.pathname==='/lookup'){
      const root=document.querySelector('[data-lookup-root]');
      const barcode=(new URLSearchParams(location.search).get('barcode')||'').replace(/\D/g,'');
      const heading=text(root?.querySelector('h1'));
      if(heading){
        if(heading.includes('這個條碼還沒有商品資料')){
          sportTrack('scan_unknown',{barcode:barcode,barcode_length:barcode.length});
        }else{
          sportTrack('scan_success',{barcode:barcode,barcode_length:barcode.length,product_name:heading});
        }
      }
    }

    document.querySelectorAll('[data-product-search]').forEach(function(input){
      let timer=null,last='';
      input.addEventListener('input',function(){
        clearTimeout(timer);
        timer=setTimeout(function(){
          const q=(input.value||'').trim();
          if(!q||q===last)return;
          last=q;
          const box=input.parentElement?.querySelector('[data-search-results]');
          const countText=text(box?.querySelector('.search-count'));
          const m=countText.match(/(\d+)/);
          sportTrack('search_product',{search_term:q,result_count:m?Number(m[1]):0});
        },700);
      });
    });

    document.addEventListener('click',function(ev){
      const a=ev.target.closest('a');
      if(!a)return;
      const href=a.getAttribute('href')||'';
      const store=storeNameFromHref(href);
      if(store){
        sportTrack('store_click',{store_name:store,link_url:new URL(href,location.href).href});
      }
      if(href.startsWith('/product/')){
        sportTrack('manual_lookup',{lookup_name:text(a),link_url:new URL(href,location.href).href});
      }
      if(a.classList.contains('search-row')){
        sportTrack('search_result_click',{product_name:text(a.querySelector('b')),link_url:new URL(href,location.href).href});
      }
      try{
        const url=new URL(href,location.href);
        if(url.hostname==='500.gov.tw'){
          sportTrack('official_link_click',{link_text:text(a),link_url:url.href});
        }
      }catch{}
    });
  });
})();
'''

(PUB / 'assets').mkdir(parents=True, exist_ok=True)
(PUB / 'assets' / 'analytics.js').write_text(ANALYTICS_JS, encoding='utf-8')

count = 0
for path in PUB.rglob('*.html'):
    html = path.read_text(encoding='utf-8')
    if MEASUREMENT_ID in html:
        continue
    if '</head>' not in html:
        continue
    html = html.replace('</head>', TAG + '</head>', 1)
    path.write_text(html, encoding='utf-8')
    count += 1

print(f'GA4 INJECTED: {MEASUREMENT_ID} into {count} HTML files')
