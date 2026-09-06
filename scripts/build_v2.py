import json, html, pathlib, unicodedata
from collections import OrderedDict

ROOT=pathlib.Path(__file__).resolve().parents[1]
PUB=ROOT/'public'
(PUB/'assets').mkdir(parents=True, exist_ok=True)
(PUB/'scan').mkdir(parents=True, exist_ok=True)
(PUB/'lookup').mkdir(parents=True, exist_ok=True)

CAT=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
MANIFEST=json.loads((ROOT/'data/official-catalog.json').read_text(encoding='utf-8'))
MANUAL=json.loads((ROOT/'data/manual-lookups.json').read_text(encoding='utf-8'))
OFFICIAL={key:json.loads((ROOT/rel).read_text(encoding='utf-8')) for key,rel in MANIFEST['stores'].items()}
BASE='https://sport.meshthings.com'


def e(value): return html.escape(str(value),quote=True)
def nfkc(value): return unicodedata.normalize('NFKC',str(value or '')).lower()

def head(title,desc,path='/',extra=''):
    canonical=BASE.rstrip('/')+(path if path.startswith('/') else '/'+path)
    if not canonical.endswith('/') and '.' not in canonical.rsplit('/',1)[-1]: canonical+='/'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f6f0df"><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="zh_TW"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><title>{e(title)}</title><link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/v2.css">{extra}</head><body>'''

def notice():
    return '<div class="top-note"><div class="wrap"><b>非官方工具</b><span>本站以官方公開清單建立搜尋索引；實際可兌換品項仍以運動部最新公告與門市 POS 為準。</span></div></div>'

def page_actions(extra=''):
    return f'<nav class="page-actions" aria-label="頁面操作"><a class="home-button" href="/">⌂ 回到首頁</a>{extra}</nav>'

def footer():
    return f'''<footer class="footer"><strong>本站不是運動部官方網站。</strong><br>資料依「揮汗有禮」活動公開資訊整理，最後整理：{CAT['updatedAt']}。實際活動規則、商品、庫存與門市結帳結果以官方公告及現場 POS 為準。<div class="footer-links"><a href="/data-status/">資料驗證報告</a><a href="https://500.gov.tw/registrant/" target="_blank" rel="noreferrer">運動部官方活動頁 ↗</a><a href="/7-eleven/">7-ELEVEN</a><a href="/familymart/">全家</a><a href="/hilife/">萊爾富</a><a href="/pxmart/">全聯</a></div></footer>'''

def jsonld(obj): return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+'</script>'
def layout(title,desc,path,body,schema=None,scripts=''):
    extra=jsonld(schema) if schema else ''
    return head(title,desc,path,extra)+notice()+body+scripts+'</body></html>'


def all_fixed_groups(store):
    return [('cat',i,c) for i,c in enumerate(store.get('categories',[]),1)]+[('bonus',i,c) for i,c in enumerate(store.get('bonusCategories',[]),1)]

def category_lookup(store,name):
    return [(prefix,idx,c) for prefix,idx,c in all_fixed_groups(store) if c['name']==name]

def item_matches(item,rule):
    text=nfkc(item)
    include=rule.get('includeAny',[])
    exclude=rule.get('excludeAny',[])
    if include and not any(nfkc(x) in text for x in include): return False
    if exclude and any(nfkc(x) in text for x in exclude): return False
    return True

def resolve_manual_for_store(store_key,lookup):
    rules=lookup.get('stores',{}).get(store_key,[])
    if not rules: return {'status':'unknown','items':[],'examples':[],'categories':[],'rawCount':0,'uniqueCount':0}
    store=OFFICIAL[store_key]
    errors=[]
    if store['mode']=='category_rules':
        cats=[]
        for rule in rules:
            target=rule.get('category')
            matches=[c for c in store['categories'] if c['name']==target]
            if not matches: errors.append(f"{lookup['id']} / {store_key}: missing category {target}")
            cats.extend(matches)
        if errors: raise SystemExit('MANUAL LOOKUP QA FAILED:\n- '+'\n- '.join(errors))
        return {'status':'category','items':[c['name'] for c in cats],'examples':[c.get('examples','') for c in cats],'categories':[c['name'] for c in cats],'rawCount':len(cats),'uniqueCount':len({c['name'] for c in cats})}
    rows=[]
    source_categories=[]
    for rule in rules:
        groups=all_fixed_groups(store) if rule.get('allCategories') else category_lookup(store,rule.get('category'))
        if not groups:
            errors.append(f"{lookup['id']} / {store_key}: missing category {rule.get('category')}")
            continue
        for prefix,idx,cat in groups:
            selected=[item for item in cat.get('items',[]) if item_matches(item,rule)]
            if selected:
                source_categories.append(cat['name'])
                rows.extend(selected)
    if errors: raise SystemExit('MANUAL LOOKUP QA FAILED:\n- '+'\n- '.join(errors))
    unique=list(OrderedDict((x,None) for x in rows).keys())
    return {'status':'exact' if rows else 'unknown','items':rows,'examples':[],'categories':list(OrderedDict((x,None) for x in source_categories).keys()),'rawCount':len(rows),'uniqueCount':len(unique)}

def resolve_manual(lookup): return {k:resolve_manual_for_store(k,lookup) for k in CAT['stores']}


def local_qa():
    errors=[]; qa={}
    seven=OFFICIAL['seven']; seven_rows=sum(len(c.get('items',[])) for c in seven['categories'])
    for c in seven['categories']:
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"7-ELEVEN {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if seven_rows!=seven['officialTotal']: errors.append(f"7-ELEVEN total {seven_rows}/{seven['officialTotal']}")
    qa['seven']={'official':seven['officialTotal'],'stored':seven_rows,'unit':'官方列數','detail':'含官方重複列示，不自行去重'}

    family=OFFICIAL['family']; family_rows=sum(len(c.get('items',[])) for c in family['categories']); family_unique=len({x for c in family['categories'] for x in c.get('items',[])})
    for c in family['categories']:
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"全家 {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if family_unique!=family['officialTotal']: errors.append(f"全家 unique {family_unique}/{family['officialTotal']}")
    qa['family']={'official':family['officialTotal'],'stored':family_unique,'unit':'不重複品項','detail':f'分類展開共 {family_rows} 列；同一商品可出現在多分類'}

    hi=OFFICIAL['hilife']; hi_rows=sum(len(c.get('items',[])) for c in hi['categories']); hi_bonus=sum(len(c.get('items',[])) for c in hi.get('bonusCategories',[]))
    for c in hi['categories']+hi.get('bonusCategories',[]):
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"萊爾富 {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if hi_rows!=hi['officialTotal']: errors.append(f"萊爾富 main {hi_rows}/{hi['officialTotal']}")
    if hi_bonus!=hi['bonusTotal']: errors.append(f"萊爾富 bonus {hi_bonus}/{hi['bonusTotal']}")
    qa['hilife']={'official':f"{hi['officialTotal']} + {hi['bonusTotal']}",'stored':f"{hi_rows} + {hi_bonus}",'unit':'品項','detail':'50 元加碼券與商品券超值加碼分開驗證'}

    for key in ('pxmart','wanjiafu','lejiakang'):
        st=OFFICIAL[key]; stored=len(st['categories'])
        if stored!=st['officialCategoryCount']: errors.append(f"{st['name']} categories {stored}/{st['officialCategoryCount']}")
        qa[key]={'official':st['officialCategoryCount'],'stored':stored,'unit':'官方類別','detail':'官方採類別制，沒有固定 SKU 總數'}

    manual_report={}
    for lookup in MANUAL['lookups']:
        resolved=resolve_manual(lookup)
        eligible=[k for k,r in resolved.items() if r['status'] in ('exact','category')]
        if not eligible: errors.append(f"manual lookup {lookup['id']} resolves to zero stores")
        manual_report[lookup['id']]={'name':lookup['name'],'eligibleStores':eligible,'stores':{k:{'status':r['status'],'rawCount':r['rawCount'],'uniqueCount':r['uniqueCount'],'categories':r['categories']} for k,r in resolved.items()}}
    if errors: raise SystemExit('LOCAL DATA QA FAILED:\n- '+'\n- '.join(errors))
    return qa,manual_report

QA,MANUAL_QA=local_qa()
(PUB/'assets/data.js').write_text('window.SPORT_DATA='+json.dumps(CAT,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/official-data.js').write_text('window.SPORT_OFFICIAL='+json.dumps(OFFICIAL,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/manual-data.js').write_text('window.SPORT_MANUAL='+json.dumps(MANUAL,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')

lookup_by_id={x['id']:x for x in MANUAL['lookups']}
popular=[x for x in MANUAL['lookups'] if x.get('popular')]
popular_html=''.join(f'<a class="quick" href="/product/{e(x["id"])}/">{e(x["name"])}</a>' for x in popular)
group_html=[]
for group in MANUAL['groups']:
    links=''.join(f'<a class="manual-link" href="/product/{e(i)}/">{e(lookup_by_id[i]["name"])}</a>' for i in group['items'])
    group_html.append(f'<div class="manual-group"><h3>{e(group["label"])}</h3><div class="manual-links">{links}</div></div>')
manual_all=f'''<details class="manual-all"><summary><span>查看全部 {len(MANUAL['lookups'])} 類</span><span>＋</span></summary><div class="manual-groups">{''.join(group_html)}</div></details>'''
store_tags=''.join(f'<span class="store-tag">{e(s["short"])}</span>' for s in CAT['stores'].values())
seo_links=''.join(['<a href="/7-eleven/">揮汗有禮 7-11 可換什麼？</a>','<a href="/familymart/">揮汗有禮全家可換什麼？</a>','<a href="/hilife/">揮汗有禮萊爾富兌換商品</a>','<a href="/product/tea-egg/">揮汗有禮茶葉蛋可以換嗎？</a>','<a href="/data-status/">資料驗證報告</a>'])
faq_schema={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"揮汗有禮可以換什麼？","acceptedAnswer":{"@type":"Answer","text":"不同通路品項不同。本站可搜尋官方完整商品清單，也可掃商品條碼；最終以官方公告與門市 POS 為準。"}},{"@type":"Question","name":"茶葉蛋、地瓜、咖啡沒有條碼怎麼查？","acceptedAnswer":{"@type":"Answer","text":"首頁提供沒有條碼或不好掃商品的完整快速入口，結果直接由官方清單與類別規則產生。"}},{"@type":"Question","name":"這是官方網站嗎？","acceptedAnswer":{"@type":"Answer","text":"不是。本站為非官方整理工具。"}}]}
home_schema={"@context":"https://schema.org","@type":"WebApplication","name":"揮汗有禮掃碼查詢","url":BASE+'/',"applicationCategory":"UtilitiesApplication","operatingSystem":"Any"}
home=f'''<main class="wrap"><header class="mast"><div class="brandline"><a href="/">揮汗有禮掃碼查詢</a><span class="date-stamp">2026 / 非官方</span></div><h1>揮汗有禮，<span class="marker">掃條碼</span><br>就知道能不能換</h1><p class="lead">拿起商品掃一下，或直接搜尋官方品名，一次看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康。</p></header><section class="scan-panel"><div class="scan-window"><div class="barcode-art"></div><div class="scan-beam"></div><div class="scan-corners"></div><span class="scan-label">對準商品條碼 → 嗶！</span></div><a class="primary" href="/scan/">▥ 掃商品條碼</a><p class="micro">條碼資料尚未完整時，不會把「沒收錄」誤判為「不能換」。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">NO BARCODE / HARD TO SCAN</div><h2>沒有條碼／不好掃，直接找</h2></div><span class="micro">現做、散裝、現調商品</span></div><p class="lead manual-intro" style="font-size:14px">這一區不再手工寫商品內容；每個入口都從官方清單或官方類別規則即時組合。</p><div class="popular-manual">{popular_html}</div>{manual_all}</section><section class="section"><div class="section-head"><div><div class="section-kicker">SEARCH ALL OFFICIAL ITEMS</div><h2>搜尋官方完整商品</h2></div></div><div class="search-wrap"><input class="search-input" data-product-search type="search" autocomplete="off" placeholder="FMC天然水610ml、FIN 580ml、原萃、拿鐵…"><span class="search-icon">⌕</span><div class="search-results" data-search-results></div></div><p class="micro">支援全形／半形、括號與容量格式正規化；結果可展開查看全部，不再默默只顯示前 10 筆。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">6 STORES</div><h2>一次查六大通路</h2></div></div><div class="store-line">{store_tags}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">POPULAR SEARCHES</div><h2>大家可能在找</h2></div></div><nav class="seo-nav">{seo_links}</nav></section><section class="section"><div class="faq"><details open><summary>「官方清單完整」是怎麼驗？</summary><p>本站把固定 SKU 通路的官方清單與分類分開保存，build 會驗證列數、分類數、全家不重複商品數與 manual lookup 引用；另有 GitHub CI 對官方網站做 live diff。</p></details><details><summary>為什麼全家會看到超過 308 列？</summary><p>全家官方標示 308 個不重複品項，但同一商品可能同時出現在不同分類。本站會同時標示「308 個不重複品項」與「分類展開列數」，避免混淆。</p></details><details><summary>這是官方網站嗎？</summary><p>不是。本站是非官方查詢工具，兌換仍以官方公告與門市 POS 為準。</p></details></div></section>{footer()}</main>'''
scripts='<script src="/assets/data.js"></script><script src="/assets/official-data.js"></script><script src="/assets/manual-data.js"></script><script src="/assets/search-core.js"></script><script src="/assets/app.js" defer></script>'
(PUB/'index.html').write_text(layout('揮汗有禮可換什麼？掃條碼查2026兌換商品｜7-11、全家、萊爾富、全聯','2026 揮汗有禮非官方商品查詢工具。可掃商品條碼、搜尋官方完整品項，茶葉蛋、地瓜、咖啡等不好掃商品也能直接查。','/',home,[home_schema,faq_schema],scripts),encoding='utf-8')

scanner=f'''<main class="wrap scanner-page">{page_actions()}<header class="mast"><div class="section-kicker">BARCODE SCANNER</div><h1>對準條碼，<span class="marker">嗶一下</span></h1><p class="lead">掃到商品後，一次看六大通路的兌換狀態。</p></header><div class="camera-shell"><video muted playsinline></video><div class="camera-frame"><span></span></div><div class="camera-status" data-camera-status>正在啟動相機…</div></div><div class="manual"><b>掃不到？手動輸入 13 碼條碼</b><form data-manual-form><input data-manual-input inputmode="numeric" maxlength="13" placeholder="例如 4716426880619"><button>查詢</button></form><p class="error" data-manual-error></p></div><div class="disclaimer"><strong>非官方查詢工具</strong><br>未知條碼只代表本站尚未建立 EAN mapping，不代表不能兌換。</div>{footer()}</main>'''
(PUB/'scan/index.html').write_text(layout('揮汗有禮掃條碼查商品｜2026 兌換商品掃描器','直接用手機相機掃商品 EAN-13 條碼，查詢揮汗有禮六大合作通路兌換狀態。','/scan/',scanner,None,'<script src="https://unpkg.com/@zxing/browser@0.2.1"></script><script src="/assets/scanner.js" defer></script>'),encoding='utf-8')
lookup_body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 再掃一個</a>')}<div data-lookup-root><div class="receipt"><b>正在查詢商品…</b></div></div>{footer()}</main>'''
lookup=layout('揮汗有禮商品掃碼結果｜非官方查詢','掃描商品條碼後顯示六大合作通路的揮汗有禮兌換狀態。','/lookup/',lookup_body,None,'<script src="/assets/data.js"></script><script src="/assets/lookup.js" defer></script>').replace('<meta name="robots" content="index,follow,max-image-preview:large">','<meta name="robots" content="noindex,follow">')
(PUB/'lookup/index.html').write_text(lookup,encoding='utf-8')

status_cls={'exact':'yes','category':'category','unknown':'unknown'}
for item in MANUAL['lookups']:
    resolved=resolve_manual(item); eligible=sum(1 for r in resolved.values() if r['status'] in ('exact','category')); rows=[]
    for key,meta in CAT['stores'].items():
        r=resolved[key]; st=r['status']; mark='✓' if st in ('exact','category') else '?'
        if st=='exact':
            label='可兌換'; detail=f"官方清單命中 {r['rawCount']} 列 / {r['uniqueCount']} 個不重複品名"; chips=''.join(f'<span class="item-chip">{e(x)}</span>' for x in r['items']); examples=''
        elif st=='category':
            label='可兌換（依官方品類）'; detail='官方採類別制'; chips=''.join(f'<span class="item-chip">{e(x)}</span>' for x in r['items']); examples=''.join(f'<div class="rule-evidence">官方舉例：{e(x)}</div>' for x in r['examples'] if x)
        else:
            label='本站無法由官方清單確認'; detail='沒有對應的固定品項或明確官方類別'; chips=''; examples=''
        cat_note=' / '.join(r['categories']) if r['categories'] else '—'
        rows.append(f'''<div class="store-result"><span class="status {status_cls[st]}">{mark}</span><div class="store-answer"><div class="store-heading"><h3>{e(meta['name'])}</h3><span class="status-label">{e(label)}</span></div><small>{e(detail)}</small>{('<div class="item-list long-list">'+chips+'</div>') if chips else ''}{examples}<div class="source-note">對應官方分類：{e(cat_note)}<br>資料來源：<a class="source" href="{e(meta['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div></div></div>''')
    title=f'揮汗有禮{item["name"]}可以換嗎？六大通路官方清單查詢'
    desc=f'查詢 2026 揮汗有禮「{item["name"]}」在六大通路的官方品項／類別，結果直接由官方資料來源產生。'
    body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">沒有條碼／不好掃，直接找</div><h1>{e(item['name'])}<br><span class="marker">哪裡可以換？</span></h1><p class="lead">這頁不再維護第二份手工商品清單；結果由官方 catalog 與對應規則直接產生。</p><div class="manual-summary"><span>{eligible} 個通路有官方依據</span><span>資料更新 {e(CAT['updatedAt'])}</span></div></header><div class="receipt"><div class="store-results">{''.join(rows)}</div></div><div class="disclaimer"><strong>判讀原則</strong><br>固定商品清單只有命中官方品名才顯示「可兌換」；官方採類別制的通路則標示「依官方品類」。沒有資料時不直接判定為不能換。</div>{footer()}</main>'''
    out=PUB/'product'/item['id']/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(layout(title,desc,f'/product/{item["id"]}/',body,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/product/{item["id"]}/'}),encoding='utf-8')


def render_category(cat,idx,prefix='cat'):
    items=''.join(f'<li>{e(x)}</li>' for x in cat.get('items',[]))
    return f'<details class="catalog-category" id="{prefix}-{idx}"><summary><span>{e(cat["name"])}</span><b>{len(cat.get("items",[]))} 列</b></summary><ol class="catalog-items">{items}</ol></details>'
def render_fixed(store):
    parts=[]
    if store.get('bonusCategories'):
        parts.append(f'<section class="catalog-group"><div class="section-kicker">商品券超值加碼</div><h2>另外加碼 {store["bonusTotal"]} 項</h2>'+''.join(render_category(c,i,'bonus') for i,c in enumerate(store['bonusCategories'],1))+'</section>')
    parts.append('<section class="catalog-group"><div class="section-kicker">OFFICIAL CATALOG</div><h2>官方分類完整展開</h2>'+''.join(render_category(c,i) for i,c in enumerate(store['categories'],1))+'</section>')
    return ''.join(parts)
def render_rules(store):
    return '<section class="catalog-group"><div class="section-kicker">OFFICIAL CATEGORY RULES</div><h2>官方完整類別</h2>'+''.join(f'<article class="rule-category" id="cat-{i}"><div><b>{e(c["name"])}</b><small>官方舉例：{e(c.get("examples",""))}</small></div><span>{i:02d}</span></article>' for i,c in enumerate(store['categories'],1))+'</section>'

for key,meta in CAT['stores'].items():
    store=OFFICIAL[key]; d=PUB/meta['slug'];d.mkdir(parents=True,exist_ok=True)
    if store['mode']=='category_rules':
        summary=f"官方採類別制，共 {store['officialCategoryCount']} 類；本站保存完整類別與官方舉例。"; count=f"{store['officialCategoryCount']} 個官方類別"; body_catalog=render_rules(store)
    elif key=='family':
        rows=sum(len(c.get('items',[])) for c in store['categories']); unique=QA[key]['stored']; summary=f"官方標示 {store['officialTotal']} 個不重複品項；分類展開共 {rows} 列，重複是因同一商品可屬於多分類。"; count=f"{unique} 個不重複品項 / {rows} 分類列"; body_catalog=render_fixed(store)
    elif key=='hilife':
        summary=f"50 元加碼券 {store['officialTotal']} 項，另有商品券超值加碼 {store['bonusTotal']} 項。"; count=f"{store['officialTotal']} + {store['bonusTotal']} 項"; body_catalog=render_fixed(store)
    else:
        summary=f"官方全部品項 {store['officialTotal']} 列；重複列示原樣保存。"; count=f"{store['officialTotal']} 官方列"; body_catalog=render_fixed(store)
    title=f'揮汗有禮 {meta["name"]} 可換什麼？2026 完整官方清單＋掃碼'
    desc=f'2026 揮汗有禮 {meta["name"]} 官方可兌換商品／類別完整非官方整理。'
    page=f'''<main class="wrap store-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">2026 揮汗有禮</div><h1>{e(meta['name'])}<br><span class="marker">可換什麼？</span></h1><p class="lead">{e(summary)}</p><div class="catalog-summary"><strong>{e(count)}</strong><span class="verified-badge">local QA 通過 ✓</span></div></header>{body_catalog}<div class="source-note catalog-source">資料來源：<a class="source" href="{e(store['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div>{footer()}</main>'''
    (d/'index.html').write_text(layout(title,desc,f'/{meta["slug"]}/',page,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/{meta["slug"]}/'}),encoding='utf-8')

qa_names={'seven':'7-ELEVEN','family':'全家','hilife':'萊爾富','pxmart':'全聯','wanjiafu':'萬家福','lejiakang':'樂家康'}
qa_rows=[]
for key in ('seven','family','hilife','pxmart','wanjiafu','lejiakang'):
    r=QA[key];qa_rows.append(f'<tr><th>{e(qa_names[key])}</th><td>{e(r["official"])} {e(r["unit"])}</td><td>{e(r["stored"])} {e(r["unit"])}</td><td>{e(r["detail"])}</td><td><span class="qa-pass">PASS</span></td></tr>')
manual_rows=[]
for item in MANUAL['lookups']:
    m=MANUAL_QA[item['id']];manual_rows.append(f'<tr><th><a href="/product/{e(item["id"])}/">{e(item["name"])}</a></th><td>{len(m["eligibleStores"])} 通路</td><td>{e("、".join(CAT["stores"][k]["short"] for k in m["eligibleStores"]))}</td><td><span class="qa-pass">PASS</span></td></tr>')
status=f'''<main class="wrap data-page">{page_actions()}<header class="mast"><div class="section-kicker">DATA QA</div><h1>資料完整性<br><span class="marker">驗證報告</span></h1><p class="lead">這頁把「本地資料結構驗證」與「官方網站 live diff」分開說明，避免再用單純數量相同就宣稱完整。</p></header><div class="qa-metrics"><div class="qa-metric"><b>6/6</b><span>通路 local 結構驗證</span></div><div class="qa-metric"><b>{len(MANUAL['lookups'])}/{len(MANUAL['lookups'])}</b><span>不好掃直接找 intents 可解析</span></div></div><section class="section"><h2>本地官方 snapshot</h2><div class="qa-scroll"><table class="qa-table"><thead><tr><th>通路</th><th>官方宣告</th><th>本站保存</th><th>說明</th><th>結果</th></tr></thead><tbody>{''.join(qa_rows)}</tbody></table></div></section><section class="section"><h2>沒有條碼／不好掃入口</h2><div class="qa-scroll"><table class="qa-table"><thead><tr><th>入口</th><th>有官方依據</th><th>通路</th><th>結果</th></tr></thead><tbody>{''.join(manual_rows)}</tbody></table></div></section><section class="section"><h2>live official diff</h2><p>GitHub CI 會直接連官方頁面，把固定商品通路逐分類比對，把全聯／萬家福／樂家康的類別與官方舉例逐列比對。只有 missing=0、extra=0、changed=0 才算通過。這個檢查與本站 JSON 的自我計數分開執行。</p></section><div class="disclaimer"><strong>非官方工具</strong><br>即使資料驗證通過，活動期間仍可能更新；門市供應與 POS 才是最終依據。</div>{footer()}</main>'''
status_dir=PUB/'data-status';status_dir.mkdir(parents=True,exist_ok=True);(status_dir/'index.html').write_text(layout('揮汗有禮資料驗證報告｜官方清單、搜尋與直接找 QA','公開本站對 2026 揮汗有禮六大通路官方資料、搜尋與不好掃商品入口的驗證方式。','/data-status/',status,{"@context":"https://schema.org","@type":"WebPage","name":"揮汗有禮資料驗證報告","url":BASE+'/data-status/'}),encoding='utf-8')

report={'updatedAt':CAT['updatedAt'],'stores':QA,'manualLookups':MANUAL_QA,'manualLookupCount':len(MANUAL['lookups'])}
(PUB/'qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
urls=['/','/scan/','/data-status/']+[f'/{s["slug"]}/' for s in CAT['stores'].values()]+[f'/product/{x["id"]}/' for x in MANUAL['lookups']]
(PUB/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
(PUB/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{u}</loc><lastmod>{CAT["updatedAt"]}</lastmod></url>' for u in urls)+'\n</urlset>',encoding='utf-8')
(PUB/'manifest.webmanifest').write_text(json.dumps({"name":"揮汗有禮掃碼查詢","short_name":"揮汗掃碼","start_url":"/","display":"standalone","background_color":"#f6f0df","theme_color":"#b6f23a"},ensure_ascii=False),encoding='utf-8')
print('LOCAL QA PASSED')
print(json.dumps(QA,ensure_ascii=False))
print('MANUAL LOOKUPS PASSED',len(MANUAL['lookups']))
print('built',len(urls),'indexable URLs')
