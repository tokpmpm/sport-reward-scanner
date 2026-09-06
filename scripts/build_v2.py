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
BARCODES=json.loads((ROOT/'data/barcodes.json').read_text(encoding='utf-8'))
OFFICIAL={key:json.loads((ROOT/rel).read_text(encoding='utf-8')) for key,rel in MANIFEST['stores'].items()}
BASE='https://sport.meshthings.com'


def e(value): return html.escape(str(value),quote=True)
def nfkc(value): return unicodedata.normalize('NFKC',str(value or '')).lower()
def uniq(values): return list(OrderedDict((x,None) for x in values).keys())

def head(title,desc,path='/',extra='',robots='index,follow,max-image-preview:large'):
    canonical=BASE.rstrip('/')+(path if path.startswith('/') else '/'+path)
    if not canonical.endswith('/') and '.' not in canonical.rsplit('/',1)[-1]: canonical+='/'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f6f0df"><meta name="description" content="{e(desc)}"><meta name="robots" content="{e(robots)}"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="zh_TW"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><title>{e(title)}</title><link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/v2.css">{extra}</head><body>'''

def notice():
    return '<div class="top-note"><div class="wrap"><b>非官方工具</b><span>實際可兌換品項請以運動部最新公告與門市 POS 為準。</span></div></div>'

def page_actions(extra=''):
    return f'<nav class="page-actions" aria-label="頁面操作"><a class="home-button" href="/">⌂ 回到首頁</a>{extra}</nav>'

def footer():
    links=''.join([
        '<a href="https://500.gov.tw/registrant/" target="_blank" rel="noreferrer">運動部官方活動頁 ↗</a>',
        '<a href="/7-eleven/">7-ELEVEN</a>','<a href="/familymart/">全家</a>','<a href="/hilife/">萊爾富</a>',
        '<a href="/pxmart/">全聯</a>','<a href="/wanjiafu/">萬家福</a>','<a href="/lejiakang/">樂家康</a>'
    ])
    return f'''<footer class="footer"><strong>本站不是運動部官方網站。</strong><br>資料依「揮汗有禮」活動公開資訊整理，最後整理：{CAT['updatedAt']}。實際活動規則、商品、庫存與門市結帳結果以官方公告及現場 POS 為準。<div class="footer-links">{links}</div></footer>'''

def jsonld(obj): return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+'</script>'
def layout(title,desc,path,body,schema=None,scripts='',robots='index,follow,max-image-preview:large'):
    extra=jsonld(schema) if schema else ''
    return head(title,desc,path,extra,robots)+notice()+body+scripts+'</body></html>'


def all_fixed_groups(store):
    return [('cat',i,c) for i,c in enumerate(store.get('categories',[]),1)]+[('bonus',i,c) for i,c in enumerate(store.get('bonusCategories',[]),1)]

def category_lookup(store,name):
    return [(prefix,idx,c) for prefix,idx,c in all_fixed_groups(store) if c['name']==name]

def item_matches(item,rule):
    text=nfkc(item); include=rule.get('includeAny',[]); exclude=rule.get('excludeAny',[])
    if include and not any(nfkc(x) in text for x in include): return False
    if exclude and any(nfkc(x) in text for x in exclude): return False
    return True

def resolve_manual_for_store(store_key,lookup):
    rules=lookup.get('stores',{}).get(store_key,[])
    if not rules: return {'status':'unknown','items':[],'examples':[],'categories':[],'rawCount':0,'uniqueCount':0}
    store=OFFICIAL[store_key]; errors=[]
    if store['mode']=='category_rules':
        cats=[]
        for rule in rules:
            target=rule.get('category'); matches=[c for c in store['categories'] if c['name']==target]
            if not matches: errors.append(f"{lookup['id']} / {store_key}: missing category {target}")
            cats.extend(matches)
        if errors: raise SystemExit('MANUAL LOOKUP QA FAILED:\n- '+'\n- '.join(errors))
        names=uniq([c['name'] for c in cats])
        return {'status':'category','items':names,'examples':[c.get('examples','') for c in cats],'categories':names,'rawCount':len(cats),'uniqueCount':len(names)}
    rows=[]; source_categories=[]
    for rule in rules:
        groups=all_fixed_groups(store) if rule.get('allCategories') else category_lookup(store,rule.get('category'))
        if not groups:
            errors.append(f"{lookup['id']} / {store_key}: missing category {rule.get('category')}"); continue
        for prefix,idx,cat in groups:
            selected=[item for item in cat.get('items',[]) if item_matches(item,rule)]
            if selected: source_categories.append(cat['name']); rows.extend(selected)
    if errors: raise SystemExit('MANUAL LOOKUP QA FAILED:\n- '+'\n- '.join(errors))
    unique=uniq(rows)
    return {'status':'exact' if rows else 'unknown','items':unique,'examples':[],'categories':uniq(source_categories),'rawCount':len(rows),'uniqueCount':len(unique)}

def resolve_manual(lookup): return {k:resolve_manual_for_store(k,lookup) for k in CAT['stores']}


def local_qa():
    errors=[]; qa={}
    seven=OFFICIAL['seven']; seven_rows=sum(len(c.get('items',[])) for c in seven['categories'])
    for c in seven['categories']:
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"7-ELEVEN {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if seven_rows!=seven['officialTotal']: errors.append(f"7-ELEVEN total {seven_rows}/{seven['officialTotal']}")
    qa['seven']={'official':seven['officialTotal'],'stored':seven_rows,'unit':'官方列數','detail':'含官方重複列示'}

    family=OFFICIAL['family']; family_rows=sum(len(c.get('items',[])) for c in family['categories']); family_unique=len({x for c in family['categories'] for x in c.get('items',[])})
    for c in family['categories']:
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"全家 {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if family_unique!=family['officialTotal']: errors.append(f"全家 unique {family_unique}/{family['officialTotal']}")
    qa['family']={'official':family['officialTotal'],'stored':family_unique,'unit':'不重複品項','detail':f'分類展開共 {family_rows} 列'}

    hi=OFFICIAL['hilife']; hi_rows=sum(len(c.get('items',[])) for c in hi['categories']); hi_bonus=sum(len(c.get('items',[])) for c in hi.get('bonusCategories',[]))
    for c in hi['categories']+hi.get('bonusCategories',[]):
        if len(c.get('items',[]))!=c['officialCount']: errors.append(f"萊爾富 {c['name']} count {len(c.get('items',[]))}/{c['officialCount']}")
    if hi_rows!=hi['officialTotal']: errors.append(f"萊爾富 main {hi_rows}/{hi['officialTotal']}")
    if hi_bonus!=hi['bonusTotal']: errors.append(f"萊爾富 bonus {hi_bonus}/{hi['bonusTotal']}")
    qa['hilife']={'official':f"{hi['officialTotal']} + {hi['bonusTotal']}",'stored':f"{hi_rows} + {hi_bonus}",'unit':'品項','detail':'一般與加碼分開'}

    for key in ('pxmart','wanjiafu','lejiakang'):
        st=OFFICIAL[key]; stored=len(st['categories'])
        if stored!=st['officialCategoryCount']: errors.append(f"{st['name']} categories {stored}/{st['officialCategoryCount']}")
        qa[key]={'official':st['officialCategoryCount'],'stored':stored,'unit':'官方類別','detail':'官方採類別制'}

    manual_report={}
    for lookup in MANUAL['lookups']:
        resolved=resolve_manual(lookup); eligible=[k for k,r in resolved.items() if r['status'] in ('exact','category')]
        if not eligible: errors.append(f"manual lookup {lookup['id']} resolves to zero stores")
        manual_report[lookup['id']]={'name':lookup['name'],'eligibleStores':eligible,'stores':{k:{'status':r['status'],'rawCount':r['rawCount'],'uniqueCount':r['uniqueCount'],'categories':r['categories']} for k,r in resolved.items()}}
    if errors: raise SystemExit('LOCAL DATA QA FAILED:\n- '+'\n- '.join(errors))
    return qa,manual_report

def gtin_ok(code):
    code=str(code)
    if len(code) not in (8,12,13,14) or not code.isdigit(): return False
    digits=[int(x) for x in code]; total=0
    for i,d in enumerate(reversed(digits[:-1])): total += d*(3 if i%2==0 else 1)
    return (10-total%10)%10==digits[-1]

def barcode_qa():
    items=BARCODES.get('items',[]); codes=[x.get('barcode','') for x in items]
    errors=[]
    if BARCODES.get('count')!=len(items): errors.append(f"barcode count field {BARCODES.get('count')}/{len(items)}")
    if len(items)!=99: errors.append(f"expected 99 barcodes, got {len(items)}")
    if len(set(codes))!=len(codes): errors.append('duplicate barcodes')
    bad=[c for c in codes if not gtin_ok(c)]
    if bad: errors.append('invalid GTIN: '+', '.join(bad))
    if errors: raise SystemExit('BARCODE QA FAILED:\n- '+'\n- '.join(errors))
    return {'count':len(items),'ean8':sum(len(c)==8 for c in codes),'ean12':sum(len(c)==12 for c in codes),'ean13':sum(len(c)==13 for c in codes)}

QA,MANUAL_QA=local_qa(); BARCODE_QA=barcode_qa()
(PUB/'assets/data.js').write_text('window.SPORT_DATA='+json.dumps(CAT,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/official-data.js').write_text('window.SPORT_OFFICIAL='+json.dumps(OFFICIAL,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/manual-data.js').write_text('window.SPORT_MANUAL='+json.dumps(MANUAL,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/barcodes.js').write_text('window.SPORT_BARCODES='+json.dumps(BARCODES,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')

lookup_by_id={x['id']:x for x in MANUAL['lookups']}
popular=[x for x in MANUAL['lookups'] if x.get('popular')]
popular_html=''.join(f'<a class="quick" href="/product/{e(x["id"])}/">{e(x["name"])}</a>' for x in popular)
group_html=[]
for group in MANUAL['groups']:
    links=''.join(f'<a class="manual-link" href="/product/{e(i)}/">{e(lookup_by_id[i]["name"])}</a>' for i in group['items'])
    group_html.append(f'<div class="manual-group"><h3>{e(group["label"])}</h3><div class="manual-links">{links}</div></div>')
manual_all=f'''<details class="manual-all"><summary><span>查看全部 {len(MANUAL['lookups'])} 類</span><span>＋</span></summary><div class="manual-groups">{''.join(group_html)}</div></details>'''
store_routes={'seven':'/7-eleven/','family':'/familymart/','hilife':'/hilife/','pxmart':'/pxmart/','wanjiafu':'/wanjiafu/','lejiakang':'/lejiakang/'}
store_tags=''.join(f'<a class="store-tag store-tag-link" href="{store_routes[k]}" aria-label="查看 {e(s["short"])} 完整可兌換商品清單"><span>{e(s["short"])}</span><span aria-hidden="true">→</span></a>' for k,s in CAT['stores'].items())
seo_links=''.join(['<a href="/7-eleven/">揮汗有禮 7-11 可換什麼？</a>','<a href="/familymart/">揮汗有禮全家可換什麼？</a>','<a href="/hilife/">揮汗有禮萊爾富兌換商品</a>','<a href="/product/tea-egg/">揮汗有禮茶葉蛋可以換嗎？</a>'])
faq_schema={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"揮汗有禮可以換什麼？","acceptedAnswer":{"@type":"Answer","text":"不同通路品項不同，可直接搜尋商品名稱或查看各通路完整清單；實際仍以官方公告與門市 POS 為準。"}},{"@type":"Question","name":"掃條碼找不到怎麼辦？","acceptedAnswer":{"@type":"Answer","text":"部分商品條碼仍在補充中，掃不到時可直接搜尋商品名稱。"}},{"@type":"Question","name":"這是官方網站嗎？","acceptedAnswer":{"@type":"Answer","text":"不是。本站為非官方整理工具。"}}]}
home_schema={"@context":"https://schema.org","@type":"WebApplication","name":"揮汗有禮商品查詢","url":BASE+'/',"applicationCategory":"UtilitiesApplication","operatingSystem":"Any"}

home=f'''<main class="wrap"><header class="mast"><div class="brandline"><a href="/">揮汗有禮商品查詢</a><span class="date-stamp">2026</span></div><h1>揮汗有禮，<span class="marker">搜商品</span><br>就知道能不能換</h1><p class="lead">輸入商品名稱，一次查看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康的官方可兌換清單。</p></header><section class="section" id="search"><div class="section-head"><div><div class="section-kicker">SEARCH</div><h2>搜尋商品</h2></div></div><div class="search-wrap"><input class="search-input" data-product-search type="search" autocomplete="off" placeholder="例如：原萃、舒跑、鮮乳、豆漿、拿鐵…"><span class="search-icon">⌕</span><div class="search-results" data-search-results></div></div></section><section class="scan-panel"><div class="section-head"><div><div class="section-kicker">BARCODE</div><h2>也可以掃條碼快速查</h2></div></div><a class="primary" href="/scan/">▥ 掃商品條碼</a><p class="micro">部分常見包裝商品可直接掃描；掃不到時可改用上方商品名稱搜尋。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">NO BARCODE</div><h2>沒有條碼／不好掃，直接找</h2></div><span class="micro">現做、散裝、現調商品</span></div><div class="popular-manual">{popular_html}</div>{manual_all}</section><section class="section"><div class="section-head"><div><div class="section-kicker">STORE CATALOGS</div><h2>六大通路完整商品清單</h2></div></div><div class="store-line">{store_tags}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">POPULAR SEARCHES</div><h2>大家可能在找</h2></div></div><nav class="seo-nav">{seo_links}</nav></section><section class="section"><div class="faq"><details open><summary>掃條碼找不到怎麼辦？</summary><p>部分商品條碼仍在補充中。掃不到不代表不能兌換，直接搜尋商品名稱即可。</p></details><details><summary>沒有條碼的茶葉蛋、地瓜、咖啡怎麼查？</summary><p>可使用上方「沒有條碼／不好掃」的快速入口。</p></details><details><summary>這是官方網站嗎？</summary><p>不是。本站是非官方查詢工具，兌換仍以官方公告與門市 POS 為準。</p></details></div></section>{footer()}</main>'''
scripts='<script src="/assets/data.js"></script><script src="/assets/official-data.js"></script><script src="/assets/manual-data.js"></script><script src="/assets/search-core.js"></script><script src="/assets/app.js" defer></script>'
(PUB/'index.html').write_text(layout('揮汗有禮可換什麼？搜尋2026兌換商品｜7-11、全家、萊爾富、全聯','2026 揮汗有禮非官方商品查詢工具。搜尋官方商品清單，也可掃部分商品條碼快速查詢。','/',home,[home_schema,faq_schema],scripts),encoding='utf-8')

scanner=f'''<main class="wrap scanner-page">{page_actions()}<header class="mast"><div class="section-kicker">BARCODE SCANNER</div><h1>對準條碼，<span class="marker">嗶一下</span></h1><p class="lead">可掃常見 8、12、13 碼商品條碼。掃不到時也能直接搜尋商品名稱。</p></header><div class="camera-shell"><video muted playsinline></video><div class="camera-frame"><span></span></div><div class="camera-status" data-camera-status>正在啟動相機…</div></div><div class="manual"><b>也可以手動輸入條碼</b><form data-manual-form><input data-manual-input inputmode="numeric" maxlength="13" placeholder="輸入 8、12 或 13 碼"><button>查詢</button></form><p class="error" data-manual-error></p></div><div class="disclaimer"><strong>掃不到也沒關係</strong><br>部分商品條碼仍在補充中，找不到時可直接改用商品名稱搜尋。</div>{footer()}</main>'''
(PUB/'scan/index.html').write_text(layout('揮汗有禮掃條碼查商品｜2026 兌換商品掃描器','用手機相機掃常見商品條碼，查詢揮汗有禮六大合作通路兌換狀態。','/scan/',scanner,None,'<script src="https://unpkg.com/@zxing/browser@0.2.1"></script><script src="/assets/scanner.js" defer></script>'),encoding='utf-8')

lookup_body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 再掃一個</a>')}<div data-lookup-root><div class="receipt"><b>正在查詢商品…</b></div></div>{footer()}</main>'''
lookup_scripts='<script src="/assets/data.js"></script><script src="/assets/official-data.js"></script><script src="/assets/manual-data.js"></script><script src="/assets/barcodes.js"></script><script src="/assets/search-core.js"></script><script src="/assets/lookup.js" defer></script>'
(PUB/'lookup/index.html').write_text(layout('揮汗有禮商品掃碼結果｜非官方查詢','掃描商品條碼後顯示六大合作通路的揮汗有禮兌換狀態。','/lookup/',lookup_body,None,lookup_scripts,'noindex,follow'),encoding='utf-8')

status_cls={'exact':'yes','category':'category','unknown':'unknown'}
for item in MANUAL['lookups']:
    resolved=resolve_manual(item); eligible=sum(1 for r in resolved.values() if r['status'] in ('exact','category')); rows=[]
    for key,meta in CAT['stores'].items():
        r=resolved[key]; st=r['status']; mark='✓' if st in ('exact','category') else '?'
        if st=='exact': label='可兌換'; detail=f"找到 {r['uniqueCount']} 個官方品項"; chips=''.join(f'<span class="item-chip">{e(x)}</span>' for x in r['items']); examples=''
        elif st=='category': label='可兌換（依官方品類）'; detail='官方開放此類商品'; chips=''.join(f'<span class="item-chip">{e(x)}</span>' for x in r['items']); examples=''.join(f'<div class="rule-evidence">例如：{e(x)}</div>' for x in r['examples'] if x)
        else: label='尚未確認'; detail='目前沒有足夠資料確認，不代表不能兌換'; chips=''; examples=''
        rows.append(f'''<div class="store-result"><span class="status {status_cls[st]}">{mark}</span><div class="store-answer"><div class="store-heading"><h3>{e(meta['name'])}</h3><span class="status-label">{e(label)}</span></div><small>{e(detail)}</small>{('<div class="item-list long-list">'+chips+'</div>') if chips else ''}{examples}<div class="source-note">資料來源：<a class="source" href="{e(meta['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div></div></div>''')
    title=f'揮汗有禮{item["name"]}可以換嗎？六大通路官方清單查詢'
    desc=f'查詢 2026 揮汗有禮「{item["name"]}」在六大通路的可兌換品項。'
    body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">沒有條碼／不好掃，直接找</div><h1>{e(item['name'])}<br><span class="marker">哪裡可以換？</span></h1><p class="lead">查看六大通路目前可確認的兌換品項。</p><div class="manual-summary"><span>{eligible} 個通路可確認</span><span>資料更新 {e(CAT['updatedAt'])}</span></div></header><div class="receipt"><div class="store-results">{''.join(rows)}</div></div><div class="disclaimer"><strong>提醒</strong><br>門市供應與實際結帳結果仍以現場 POS 為準。</div>{footer()}</main>'''
    out=PUB/'product'/item['id']/'index.html'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(layout(title,desc,f'/product/{item["id"]}/',body,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/product/{item["id"]}/'}),encoding='utf-8')


def render_category(cat,idx,prefix='cat'):
    items=uniq(cat.get('items',[])); lis=''.join(f'<li>{e(x)}</li>' for x in items)
    return f'<details class="catalog-category" id="{prefix}-{idx}"><summary><span>{e(cat["name"])}</span><b>{len(items)} 項</b></summary><ol class="catalog-items">{lis}</ol></details>'
def render_fixed(store):
    parts=[]
    if store.get('bonusCategories'):
        parts.append(f'<section class="catalog-group"><div class="section-kicker">商品券超值加碼</div><h2>另外加碼 {store["bonusTotal"]} 項</h2>'+''.join(render_category(c,i,'bonus') for i,c in enumerate(store['bonusCategories'],1))+'</section>')
    parts.append('<section class="catalog-group"><div class="section-kicker">OFFICIAL CATALOG</div><h2>官方商品清單</h2>'+''.join(render_category(c,i) for i,c in enumerate(store['categories'],1))+'</section>')
    return ''.join(parts)
def render_rules(store):
    return '<section class="catalog-group"><div class="section-kicker">OFFICIAL CATEGORIES</div><h2>官方可兌換類別</h2>'+''.join(f'<article class="rule-category" id="cat-{i}"><div><b>{e(c["name"])}</b><small>{("例如："+e(c.get("examples",""))) if c.get("examples") else ""}</small></div><span>{i:02d}</span></article>' for i,c in enumerate(store['categories'],1))+'</section>'

for key,meta in CAT['stores'].items():
    store=OFFICIAL[key]; d=PUB/meta['slug']; d.mkdir(parents=True,exist_ok=True)
    if store['mode']=='category_rules': summary=f"官方開放 {store['officialCategoryCount']} 個商品類別。"; count=f"{store['officialCategoryCount']} 個類別"; body_catalog=render_rules(store)
    elif key=='family': summary=f"官方列出 {store['officialTotal']} 個不重複品項，依分類整理如下。"; count=f"{store['officialTotal']} 個品項"; body_catalog=render_fixed(store)
    elif key=='hilife': summary=f"50 元加碼券 {store['officialTotal']} 項，另有商品券超值加碼 {store['bonusTotal']} 項。"; count=f"{store['officialTotal']} + {store['bonusTotal']} 項"; body_catalog=render_fixed(store)
    else: summary=f"官方清單共 {store['officialTotal']} 項列示；同分類的同名商品在畫面上只顯示一次。"; count=f"{store['officialTotal']} 項官方列示"; body_catalog=render_fixed(store)
    title=f'揮汗有禮 {meta["name"]} 可換什麼？2026 完整官方清單＋掃碼'; desc=f'2026 揮汗有禮 {meta["name"]} 官方可兌換商品／類別完整非官方整理。'
    page=f'''<main class="wrap store-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">2026 揮汗有禮</div><h1>{e(meta['name'])}<br><span class="marker">可換什麼？</span></h1><p class="lead">{e(summary)}</p><div class="catalog-summary"><strong>{e(count)}</strong></div></header>{body_catalog}<div class="source-note catalog-source">資料來源：<a class="source" href="{e(store['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div>{footer()}</main>'''
    (d/'index.html').write_text(layout(title,desc,f'/{meta["slug"]}/',page,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/{meta["slug"]}/'}),encoding='utf-8')

# Internal QA page: kept for maintenance, but hidden from navigation/search engines.
qa_names={'seven':'7-ELEVEN','family':'全家','hilife':'萊爾富','pxmart':'全聯','wanjiafu':'萬家福','lejiakang':'樂家康'}
qa_rows=[]
for key in ('seven','family','hilife','pxmart','wanjiafu','lejiakang'):
    r=QA[key]; qa_rows.append(f'<tr><th>{e(qa_names[key])}</th><td>{e(r["official"])} {e(r["unit"])}</td><td>{e(r["stored"])} {e(r["unit"])}</td><td>{e(r["detail"])}</td><td><span class="qa-pass">PASS</span></td></tr>')
status=f'''<main class="wrap data-page">{page_actions()}<header class="mast"><div class="section-kicker">INTERNAL DATA QA</div><h1>內部資料驗證</h1></header><div class="qa-metrics"><div class="qa-metric"><b>6/6</b><span>通路資料結構</span></div><div class="qa-metric"><b>{BARCODE_QA['count']}</b><span>已驗證條碼</span></div></div><section class="section"><div class="qa-scroll"><table class="qa-table"><thead><tr><th>通路</th><th>官方宣告</th><th>本站保存</th><th>說明</th><th>結果</th></tr></thead><tbody>{''.join(qa_rows)}</tbody></table></div></section></main>'''
status_dir=PUB/'data-status'; status_dir.mkdir(parents=True,exist_ok=True); (status_dir/'index.html').write_text(layout('內部資料驗證','內部維護用資料驗證頁。','/data-status/',status,None,'','noindex,nofollow'),encoding='utf-8')

report={'updatedAt':CAT['updatedAt'],'stores':QA,'manualLookups':MANUAL_QA,'manualLookupCount':len(MANUAL['lookups']),'barcodes':BARCODE_QA}
(PUB/'qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
urls=['/','/scan/']+[f'/{s["slug"]}/' for s in CAT['stores'].values()]+[f'/product/{x["id"]}/' for x in MANUAL['lookups']]
(PUB/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
(PUB/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{u}</loc><lastmod>{CAT["updatedAt"]}</lastmod></url>' for u in urls)+'\n</urlset>',encoding='utf-8')
(PUB/'manifest.webmanifest').write_text(json.dumps({"name":"揮汗有禮商品查詢","short_name":"揮汗查詢","start_url":"/","display":"standalone","background_color":"#f6f0df","theme_color":"#b6f23a"},ensure_ascii=False),encoding='utf-8')
print('LOCAL QA PASSED')
print('BARCODE QA PASSED',json.dumps(BARCODE_QA,ensure_ascii=False))
print('MANUAL LOOKUPS PASSED',len(MANUAL['lookups']))
print('built',len(urls),'indexable URLs')
