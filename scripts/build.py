import json, html, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
PUB=ROOT/'public'
(PUB/'assets').mkdir(parents=True, exist_ok=True)
(PUB/'scan').mkdir(parents=True, exist_ok=True)
(PUB/'lookup').mkdir(parents=True, exist_ok=True)

CAT=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
MANIFEST=json.loads((ROOT/'data/official-catalog.json').read_text(encoding='utf-8'))
OFFICIAL={}
for key, rel in MANIFEST['stores'].items():
    OFFICIAL[key]=json.loads((ROOT/rel).read_text(encoding='utf-8'))

BASE='https://sport.meshthings.com'

def e(s):
    return html.escape(str(s), quote=True)

def head(title, desc, path='/', extra=''):
    canonical=BASE.rstrip('/') + (path if path.startswith('/') else '/'+path)
    if not canonical.endswith('/') and '.' not in canonical.rsplit('/',1)[-1]:
        canonical += '/'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f6f0df"><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="zh_TW"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><title>{e(title)}</title><link rel="stylesheet" href="/assets/site.css">{extra}</head><body>'''

def notice():
    return '<div class="top-note"><div class="wrap"><b>非官方工具</b><span>資料可能有遺漏或誤植，實際可兌換品項請以運動部官方最新公告與門市 POS 為準。</span></div></div>'

def page_actions(extra=''):
    return f'<nav class="page-actions" aria-label="頁面操作"><a class="home-button" href="/">⌂ 回到首頁</a>{extra}</nav>'

def footer():
    return f'''<footer class="footer"><strong>本站不是運動部官方網站。</strong><br>資料依「揮汗有禮」活動公開資訊整理，最後整理：{CAT['updatedAt']}。實際活動規則、商品、庫存與門市結帳結果以官方公告及現場 POS 為準。<div class="footer-links"><a href="/data-status/">資料完整度 ✓</a><a href="https://500.gov.tw/registrant/" target="_blank" rel="noreferrer">運動部官方活動頁 ↗</a><a href="/7-eleven/">7-ELEVEN</a><a href="/familymart/">全家</a><a href="/hilife/">萊爾富</a><a href="/pxmart/">全聯</a></div></footer>'''

def jsonld(obj):
    return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+'</script>'

def layout(title,desc,path,body,schema=None,scripts=''):
    extra=jsonld(schema) if schema else ''
    return head(title,desc,path,extra)+notice()+body+scripts+'</body></html>'

def validate_official():
    errors=[]
    qa={}
    seven=OFFICIAL['seven']
    seven_stored=sum(len(c.get('items',[])) for c in seven['categories'])
    for c in seven['categories']:
        if len(c.get('items',[])) != c['officialCount']:
            errors.append(f"7-ELEVEN {c['name']}: {len(c.get('items',[]))}/{c['officialCount']}")
    if seven_stored != seven['officialTotal']:
        errors.append(f"7-ELEVEN total: {seven_stored}/{seven['officialTotal']}")
    qa['seven']={'official':seven['officialTotal'],'stored':seven_stored,'unit':'品項','note':'29 個官方分類，重複列示品項原樣保留'}

    family=OFFICIAL['family']
    for c in family['categories']:
        if len(c.get('items',[])) != c['officialCount']:
            errors.append(f"全家 {c['name']}: {len(c.get('items',[]))}/{c['officialCount']}")
    family_unique=len(set(item for c in family['categories'] for item in c.get('items',[])))
    if family_unique != family['officialTotal']:
        errors.append(f"Family unique total: {family_unique}/{family['officialTotal']}")
    qa['family']={'official':family['officialTotal'],'stored':family_unique,'unit':'不重複品項','note':'官方分類有重疊，分類列示合計可能大於 308'}

    hi=OFFICIAL['hilife']
    hi_stored=sum(len(c.get('items',[])) for c in hi['categories'])
    hi_bonus=sum(len(c.get('items',[])) for c in hi.get('bonusCategories',[]))
    for c in hi['categories']+hi.get('bonusCategories',[]):
        if len(c.get('items',[])) != c['officialCount']:
            errors.append(f"萊爾富 {c['name']}: {len(c.get('items',[]))}/{c['officialCount']}")
    if hi_stored != hi['officialTotal']:
        errors.append(f"Hi-Life total: {hi_stored}/{hi['officialTotal']}")
    if hi_bonus != hi['bonusTotal']:
        errors.append(f"Hi-Life bonus: {hi_bonus}/{hi['bonusTotal']}")
    qa['hilife']={'official':f"{hi['officialTotal']} + {hi['bonusTotal']}",'stored':f"{hi_stored} + {hi_bonus}",'unit':'品項','note':'168 個 50 元加碼券品項＋7 個商品券超值加碼品項'}

    for key in ('pxmart','wanjiafu','lejiakang'):
        x=OFFICIAL[key]
        stored=len(x['categories'])
        if stored != x['officialCategoryCount']:
            errors.append(f"{x['name']} categories: {stored}/{x['officialCategoryCount']}")
        qa[key]={'official':x['officialCategoryCount'],'stored':stored,'unit':'官方類別','note':'官方採類別制，沒有列出固定 SKU 總數'}

    if errors:
        raise SystemExit("OFFICIAL CATALOG QA FAILED:\n- " + "\n- ".join(errors))
    return qa

QA=validate_official()

(PUB/'assets/data.js').write_text('window.SPORT_DATA='+json.dumps(CAT,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
(PUB/'assets/official-data.js').write_text('window.SPORT_OFFICIAL='+json.dumps(OFFICIAL,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')

quick=[p for p in CAT['products'] if p.get('quick')]
store_tags=''.join(f'<span class="store-tag">{e(s["short"])}</span>' for s in CAT['stores'].values())
quick_html=''.join(f'<a class="quick" href="/product/{e(p["id"])}/">{e(p["name"])}</a>' for p in quick)
seo_links=''.join([
    '<a href="/7-eleven/">揮汗有禮 7-11 可換什麼？</a>',
    '<a href="/familymart/">揮汗有禮全家可換什麼？</a>',
    '<a href="/hilife/">揮汗有禮萊爾富兌換商品</a>',
    '<a href="/product/tea-egg/">揮汗有禮茶葉蛋可以換嗎？</a>',
    '<a href="/data-status/">官方品項完整度驗證 ✓</a>'
])
faq_schema={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {"@type":"Question","name":"揮汗有禮可以換什麼？","acceptedAnswer":{"@type":"Answer","text":"不同合作通路的兌換商品不同。本站可掃描商品條碼，一次查看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康的整理結果；實際以官方公告與門市 POS 為準。"}},
    {"@type":"Question","name":"茶葉蛋、地瓜沒有條碼怎麼查？","acceptedAnswer":{"@type":"Answer","text":"可直接使用首頁的無條碼商品快速查詢，查看各通路官方品名或開放類別。"}},
    {"@type":"Question","name":"這是運動部官方網站嗎？","acceptedAnswer":{"@type":"Answer","text":"不是。本站是非官方整理工具，資料可能有遺漏或誤植，最終以運動部官方公告及門市 POS 為準。"}}
]}
home_schema={"@context":"https://schema.org","@type":"WebApplication","name":"揮汗有禮掃碼查詢","url":BASE+"/","applicationCategory":"UtilitiesApplication","operatingSystem":"Any","description":"直接掃商品條碼，一次查詢揮汗有禮六大合作通路兌換狀態的非官方工具。"}
body=f'''<main class="wrap"><header class="mast"><div class="brandline"><a href="/">揮汗有禮掃碼查詢</a><span class="date-stamp">2026 / 非官方</span></div><h1>揮汗有禮，<span class="marker">掃條碼</span><br>就知道能不能換</h1><p class="lead">不用站在貨架前慢慢對清單。拿起商品掃一下，一次看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康。</p></header><section class="scan-panel" aria-label="掃碼入口"><div class="scan-window"><div class="barcode-art" aria-hidden="true"></div><div class="scan-beam" aria-hidden="true"></div><div class="scan-corners" aria-hidden="true"></div><span class="scan-label">對準商品條碼 → 嗶！</span></div><a class="primary" href="/scan/">▥ 掃商品條碼</a><p class="micro">掃到後會直接列出其他通路是否也有可兌換品項。掃不到仍可用商品名稱查詢。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">NO BARCODE? NO PROBLEM.</div><h2>沒有條碼，直接找</h2></div><span class="micro">茶葉蛋、地瓜、咖啡也能查</span></div><div class="quick-grid">{quick_html}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">SEARCH</div><h2>搜尋商品</h2></div></div><div class="search-wrap"><input class="search-input" data-product-search type="search" autocomplete="off" placeholder="茶葉蛋、寶礦力、地瓜、豆漿…"><span class="search-icon">⌕</span><div class="search-results" data-search-results></div></div><p class="micro">搜尋會同時查本站條碼資料與官方完整品項／類別。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">6 STORES</div><h2>一次查六大通路</h2></div></div><div class="store-line">{store_tags}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">POPULAR SEARCHES</div><h2>大家可能在找</h2></div></div><nav class="seo-nav">{seo_links}</nav></section><section class="section"><div class="faq"><details open><summary>揮汗有禮可以換什麼？</summary><p>每個合作通路的商品不同。這個工具的重點不是再做一張很長的清單，而是讓你直接掃手上的商品條碼，一次看哪些通路有可兌換品項。</p></details><details><summary>茶葉蛋、地瓜沒有條碼怎麼辦？</summary><p>直接點上方常見商品或搜尋品名。結果頁會把各通路的官方品名直接列出，不需要跳去官網自己找。</p></details><details><summary>這是官方網站嗎？</summary><p>不是。本站是非官方整理工具，資料可能有遺漏或誤植。實際兌換請以運動部官方最新公告及門市 POS 為準。</p></details></div></section>{footer()}</main>'''
(PUB/'index.html').write_text(layout('揮汗有禮可換什麼？掃條碼查2026兌換商品｜7-11、全家、萊爾富、全聯','2026 揮汗有禮非官方商品查詢工具。直接掃商品條碼，一次確認 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康哪些通路可以兌換；官方完整品項與類別也可直接搜尋。','/',body,[home_schema,faq_schema],'<script src="/assets/data.js"></script><script src="/assets/official-data.js"></script><script src="/assets/app.js" defer></script>'),encoding='utf-8')

scanner_body=f'''<main class="wrap scanner-page">{page_actions()}<header class="mast"><div class="section-kicker">BARCODE SCANNER</div><h1>對準條碼，<span class="marker">嗶一下</span></h1><p class="lead">掃到商品後，直接一次看六大通路的兌換狀態。</p></header><div class="camera-shell"><video muted playsinline></video><div class="camera-frame"><span></span></div><div class="camera-status" data-camera-status>正在啟動相機…</div></div><div class="manual"><b>掃不到？手動輸入 13 碼條碼</b><form data-manual-form><input data-manual-input inputmode="numeric" maxlength="13" placeholder="例如 4716426880619"><button>查詢</button></form><p class="error" data-manual-error></p></div><div class="disclaimer"><strong>非官方查詢工具</strong><br>掃描結果依本站整理資料判定，可能有遺漏或誤植；實際可兌換商品以官方公告及門市 POS 為準。</div>{footer()}</main>'''
(PUB/'scan/index.html').write_text(layout('揮汗有禮掃條碼查商品｜2026 兌換商品掃描器','直接用手機相機掃商品 EAN-13 條碼，查詢揮汗有禮六大合作通路兌換狀態。非官方工具，結果以官方與門市 POS 為準。','/scan/',scanner_body,None,'<script src="https://unpkg.com/@zxing/browser@0.2.1"></script><script src="/assets/scanner.js" defer></script>'),encoding='utf-8')

lookup_body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 再掃一個</a>')}<div data-lookup-root><div class="receipt"><b>正在查詢商品…</b></div></div>{footer()}</main>'''
lookup=layout('揮汗有禮商品掃碼結果｜非官方查詢','掃描商品條碼後顯示六大合作通路的揮汗有禮兌換狀態。','/lookup/',lookup_body,None,'<script src="/assets/data.js"></script><script src="/assets/lookup.js" defer></script>').replace('<meta name="robots" content="index,follow,max-image-preview:large">','<meta name="robots" content="noindex,follow">')
(PUB/'lookup/index.html').write_text(lookup,encoding='utf-8')

status_label={'exact':'可兌換','category':'可兌換（依官方品類）','unknown':'尚未確認','no':'不適用'}
status_cls={'exact':'yes','category':'category','unknown':'unknown','no':'unknown'}
for p in quick:
    rows=[]; eligible=0
    for k,s in CAT['stores'].items():
        rec=p['stores'].get(k,{'status':'unknown','items':[]}); st=rec['status']
        if st in ('exact','category'): eligible+=1
        chips=''.join(f'<span class="item-chip">{e(x)}</span>' for x in rec.get('items',[]))
        rows.append(f'''<div class="store-result"><span class="status {status_cls.get(st,'unknown')}">{'✓' if st in ('exact','category') else '?'}</span><div class="store-answer"><div class="store-heading"><h3>{e(s['name'])}</h3><span class="status-label">{status_label.get(st,'尚未確認')}</span></div><small>{'官方品項明列' if st=='exact' else '符合官方開放品類' if st=='category' else '本站目前資料不足'}</small>{('<div class="item-list">'+chips+'</div>') if chips else ''}<div class="source-note">資料來源：<a class="source" href="{e(s['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div></div></div>''')
    title=f'揮汗有禮{p["name"]}可以換嗎？7-11、全家、萊爾富兌換查詢'
    desc=f'查詢 2026 揮汗有禮「{p["name"]}」在哪些通路可以兌換，直接整理 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康品項。非官方工具，以官方與門市 POS 為準。'
    schema={"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/product/{p["id"]}/',"description":desc}
    body=f'''<main class="wrap product-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">揮汗有禮商品查詢</div><h1>{e(p['name'])}<br><span class="marker">哪裡可以換？</span></h1><p class="lead">沒有固定條碼也不用一間一間翻清單。下面直接列各通路目前整理到的官方品名／開放品類。</p></header><div class="receipt"><div class="receipt-top"><div><span class="stamp">{eligible} 個通路有可兌換品項</span><div class="receipt-meta" style="margin-top:10px">最後整理：{CAT['updatedAt']}</div></div></div><div class="store-results">{''.join(rows)}</div></div>{('<div class="disclaimer"><strong>品項提醒</strong><br>'+e(p.get('note',''))+'</div>') if p.get('note') else ''}<div class="disclaimer"><strong>本站不是官方網站</strong><br>資料可能有遺漏或誤植，實際商品、規格、庫存及結帳結果請以運動部官方最新公告與門市 POS 為準。</div>{footer()}</main>'''
    out=PUB/'product'/p['id']/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(layout(title,desc,f'/product/{p["id"]}/',body,schema),encoding='utf-8')

def render_category(cat, idx, prefix='cat'):
    items=''.join(f'<li>{e(item)}</li>' for item in cat.get('items',[]))
    return f'''<details class="catalog-category" id="{prefix}-{idx}"><summary><span>{e(cat['name'])}</span><b>{cat['officialCount']} 項</b></summary><ol class="catalog-items">{items}</ol></details>'''

def render_fixed_categories(store):
    parts=[]
    if store.get('bonusCategories'):
        bonus=''.join(render_category(cat, i, prefix='bonus') for i,cat in enumerate(store['bonusCategories'],1))
        parts.append(f'''<section class="catalog-group"><div class="section-kicker">商品券超值加碼</div><h2>另外加碼 {store['bonusTotal']} 項</h2>{bonus}</section>''')
    parts.append('<section class="catalog-group"><div class="section-kicker">OFFICIAL CATALOG</div><h2>官方完整清單</h2>')
    parts.extend(render_category(cat,i) for i,cat in enumerate(store['categories'],1))
    parts.append('</section>')
    return ''.join(parts)

def render_rule_categories(store):
    return '<section class="catalog-group"><div class="section-kicker">OFFICIAL CATEGORY RULES</div><h2>官方完整類別</h2>'+''.join(
        f'''<article class="rule-category" id="cat-{i}"><div><b>{e(c['name'])}</b><small>官方舉例：{e(c.get('examples',''))}</small></div><span>{i:02d}</span></article>'''
        for i,c in enumerate(store['categories'],1)
    )+'</section>'

for k,s in CAT['stores'].items():
    slug=s['slug']; d=PUB/slug; d.mkdir(parents=True,exist_ok=True)
    off=OFFICIAL[k]
    if off['mode']=='category_rules':
        summary=f"官方以 {off['officialCategoryCount']} 個可兌換類別公告，並非固定 SKU 清單。本站已完整保存所有類別與官方舉例。"
        catalog_html=render_rule_categories(off)
        count_label=f"{off['officialCategoryCount']} 個官方類別"
    elif k=='family':
        summary=f"官方標示全部品項 {off['officialTotal']} 項；因同一商品可能出現在多個分類，本站以不重複商品名稱驗證為 {QA[k]['stored']} 項。"
        catalog_html=render_fixed_categories(off)
        count_label=f"{off['officialTotal']} 個不重複品項"
    elif k=='hilife':
        summary=f"官方 50 元加碼券共 {off['officialTotal']} 項，另有商品券超值加碼 {off['bonusTotal']} 項；本站兩區都完整保存。"
        catalog_html=render_fixed_categories(off)
        count_label=f"{off['officialTotal']} + {off['bonusTotal']} 項"
    else:
        summary=f"官方全部品項 {off['officialTotal']} 項，本站逐分類原樣保存；官方重複列出的品項不自行刪除。"
        catalog_html=render_fixed_categories(off)
        count_label=f"{off['officialTotal']} 項"

    title=f'揮汗有禮 {s["name"]} 可換什麼？2026 完整兌換商品清單＋掃碼'
    desc=f'2026 揮汗有禮 {s["name"]} 官方可兌換商品／類別完整非官方整理，並提供手機掃條碼快速確認。本站資料以官方公告與門市 POS 為準。'
    body=f'''<main class="wrap store-page">{page_actions('<a class="secondary-button" href="/scan/">▥ 掃商品條碼</a>')}<header class="mast"><div class="section-kicker">2026 揮汗有禮</div><h1>{e(s['name'])}<br><span class="marker">可換什麼？</span></h1><p class="lead">{e(summary)}</p><div class="catalog-summary"><strong>{e(count_label)}</strong><span class="verified-badge">本站 QA 通過 ✓</span></div></header>{catalog_html}<div class="source-note catalog-source">資料來源：<a class="source" href="{e(off['source'])}" target="_blank" rel="noreferrer">運動部官方清單 ↗</a></div><div class="disclaimer"><strong>非官方整理</strong><br>本站完整性驗證只代表「本站保存的清單數量與目前官方頁一致」，不保證活動期間官方不會更新；實際兌換資格、規格、庫存與門市 POS 仍以官方最新公告為準。</div>{footer()}</main>'''
    (d/'index.html').write_text(layout(title,desc,f'/{slug}/',body,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/{slug}/'}),encoding='utf-8')

qa_names={'seven':'7-ELEVEN','family':'全家','hilife':'萊爾富','pxmart':'全聯','wanjiafu':'萬家福','lejiakang':'樂家康'}
qa_rows=[]
for key in ('seven','family','hilife','pxmart','wanjiafu','lejiakang'):
    r=QA[key]
    qa_rows.append(f'''<tr><th scope="row"><a href="/{CAT['stores'][key]['slug']}/">{e(qa_names[key])}</a></th><td>{e(r['official'])} {e(r['unit'])}</td><td>{e(r['stored'])} {e(r['unit'])}</td><td><span class="qa-pass">完整 ✓</span></td></tr>''')
status_body=f'''<main class="wrap data-page">{page_actions()}<header class="mast"><div class="section-kicker">DATA QA</div><h1>官方品項<br><span class="marker">完整度驗證</span></h1><p class="lead">這張表不是用人工目測，而是每次 build 都重新計算。數量不一致時，部署會直接失敗。</p></header><div class="qa-scroll"><table class="qa-table"><thead><tr><th>通路</th><th>官方</th><th>本站</th><th>結果</th></tr></thead><tbody>{''.join(qa_rows)}</tbody></table></div><section class="section"><h2>怎麼判定「完整」？</h2><div class="qa-notes"><p><b>7-ELEVEN：</b>逐分類計數，總列數必須等於 473；官方重複列示的商品不去重。</p><p><b>全家：</b>官方分類彼此有重疊，因此以所有分類商品名稱去重後必須等於官方標示的 308 項。</p><p><b>萊爾富：</b>50 元加碼券 168 項與商品券超值加碼 7 項分開核對。</p><p><b>全聯、萬家福、樂家康：</b>官方本身採「可兌換類別」公告，因此驗證的是官方類別是否完整保存，不宣稱有固定 SKU 總數。</p></div></section><div class="disclaimer"><strong>仍可能有錯誤</strong><br>本站是非官方工具。完整度 QA 可以防止漏列，但無法保證官方頁面文字本身沒有異動或資料解讀錯誤；實際兌換仍以運動部最新公告與門市 POS 為準。</div>{footer()}</main>'''
status_dir=PUB/'data-status';status_dir.mkdir(parents=True,exist_ok=True)
(status_dir/'index.html').write_text(layout('揮汗有禮商品清單完整度｜六大通路官方資料 QA','本站逐通路核對 2026 揮汗有禮官方商品與類別數量，公開 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康資料完整度。','/data-status/',status_body,{"@context":"https://schema.org","@type":"WebPage","name":"揮汗有禮商品清單完整度","url":BASE+'/data-status/'}),encoding='utf-8')

urls=['/','/scan/','/data-status/']+[f'/{s["slug"]}/' for s in CAT['stores'].values()]+[f'/product/{p["id"]}/' for p in quick]
(PUB/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
(PUB/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{u}</loc><lastmod>{CAT["updatedAt"]}</lastmod></url>' for u in urls)+'\n</urlset>',encoding='utf-8')
(PUB/'manifest.webmanifest').write_text(json.dumps({"name":"揮汗有禮掃碼查詢","short_name":"揮汗掃碼","start_url":"/","display":"standalone","background_color":"#f6f0df","theme_color":"#b6f23a"},ensure_ascii=False),encoding='utf-8')

print('official QA passed:', json.dumps(QA, ensure_ascii=False))
print('built',len(urls),'indexable URLs')
