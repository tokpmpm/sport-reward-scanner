import json, html, os, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
PUB=ROOT/'public'
(PUB/'assets').mkdir(parents=True, exist_ok=True)
(PUB/'scan').mkdir(parents=True, exist_ok=True)
(PUB/'lookup').mkdir(parents=True, exist_ok=True)
CAT=json.loads((ROOT/'data/catalog.json').read_text())
BASE='https://sport.meshthings.com'

def e(s): return html.escape(str(s), quote=True)

def head(title, desc, path='/', extra=''):
    canonical=BASE.rstrip('/') + (path if path.startswith('/') else '/'+path)
    if not canonical.endswith('/') and '.' not in canonical.rsplit('/',1)[-1]: canonical += '/'
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f6f0df"><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="website"><meta property="og:locale" content="zh_TW"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><title>{e(title)}</title><link rel="stylesheet" href="/assets/site.css">{extra}</head><body>'''

def notice():
    return '<div class="top-note"><div class="wrap"><b>非官方工具</b><span>資料可能有遺漏或誤植，實際可兌換品項請以運動部官方最新公告與門市 POS 為準。</span></div></div>'

def footer():
    return f'''<footer class="footer"><strong>本站不是運動部官方網站。</strong><br>資料依「揮汗有禮」活動公開資訊整理，最後整理：{CAT['updatedAt']}。實際活動規則、商品、庫存與門市結帳結果以官方公告及現場 POS 為準。<div class="footer-links"><a href="https://500.gov.tw/registrant/" target="_blank" rel="noreferrer">運動部官方活動頁 ↗</a><a href="/7-eleven/">7-ELEVEN</a><a href="/familymart/">全家</a><a href="/hilife/">萊爾富</a><a href="/pxmart/">全聯</a></div></footer>'''

def jsonld(obj):
    return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+'</script>'

def layout(title,desc,path,body,schema=None,scripts=''):
    extra=jsonld(schema) if schema else ''
    return head(title,desc,path,extra)+notice()+body+scripts+'</body></html>'

(PUB/'assets/data.js').write_text('window.SPORT_DATA='+json.dumps(CAT,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')

quick=[p for p in CAT['products'] if p.get('quick')]
store_tags=''.join(f'<span class="store-tag">{e(s["short"])}</span>' for s in CAT['stores'].values())
quick_html=''.join(f'<a class="quick" href="/product/{e(p["id"])}/">{e(p["name"])}</a>' for p in quick)
seo_links=''.join([
    '<a href="/7-eleven/">揮汗有禮 7-11 可換什麼？</a>',
    '<a href="/familymart/">揮汗有禮全家可換什麼？</a>',
    '<a href="/hilife/">揮汗有禮萊爾富兌換商品</a>',
    '<a href="/product/tea-egg/">揮汗有禮茶葉蛋可以換嗎？</a>'
])
faq_schema={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {"@type":"Question","name":"揮汗有禮可以換什麼？","acceptedAnswer":{"@type":"Answer","text":"不同合作通路的兌換商品不同。本站可掃描商品條碼，一次查看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康的整理結果；實際以官方公告與門市 POS 為準。"}},
    {"@type":"Question","name":"茶葉蛋、地瓜沒有條碼怎麼查？","acceptedAnswer":{"@type":"Answer","text":"可直接使用首頁的無條碼商品快速查詢，查看各通路官方品名或開放類別。"}},
    {"@type":"Question","name":"這是運動部官方網站嗎？","acceptedAnswer":{"@type":"Answer","text":"不是。本站是非官方整理工具，資料可能有遺漏或誤植，最終以運動部官方公告及門市 POS 為準。"}}
]}
home_schema={"@context":"https://schema.org","@type":"WebApplication","name":"揮汗有禮掃碼查詢","url":BASE+'/',"applicationCategory":"UtilitiesApplication","operatingSystem":"Any","description":"直接掃商品條碼，一次查詢揮汗有禮六大合作通路兌換狀態的非官方工具。"}
body=f'''<main class="wrap"><header class="mast"><div class="brandline"><a href="/">揮汗有禮掃碼查詢</a><span class="date-stamp">2026 / 非官方</span></div><h1>揮汗有禮，<span class="marker">掃條碼</span><br>就知道能不能換</h1><p class="lead">不用站在貨架前慢慢對清單。拿起商品掃一下，一次看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康。</p></header><section class="scan-panel" aria-label="掃碼入口"><div class="scan-window"><div class="barcode-art" aria-hidden="true"></div><div class="scan-beam" aria-hidden="true"></div><div class="scan-corners" aria-hidden="true"></div><span class="scan-label">對準商品條碼 → 嗶！</span></div><a class="primary" href="/scan/">▥ 掃商品條碼</a><p class="micro">掃到後會直接列出其他通路是否也有可兌換品項。掃不到仍可用商品名稱查詢。</p></section><section class="section"><div class="section-head"><div><div class="section-kicker">NO BARCODE? NO PROBLEM.</div><h2>沒有條碼，直接找</h2></div><span class="micro">茶葉蛋、地瓜、咖啡也能查</span></div><div class="quick-grid">{quick_html}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">SEARCH</div><h2>搜尋商品</h2></div></div><div class="search-wrap"><input class="search-input" data-product-search type="search" autocomplete="off" placeholder="茶葉蛋、寶礦力、地瓜、豆漿…"><span class="search-icon">⌕</span><div class="search-results" data-search-results></div></div></section><section class="section"><div class="section-head"><div><div class="section-kicker">6 STORES</div><h2>一次查六大通路</h2></div></div><div class="store-line">{store_tags}</div></section><section class="section"><div class="section-head"><div><div class="section-kicker">POPULAR SEARCHES</div><h2>大家可能在找</h2></div></div><nav class="seo-nav">{seo_links}</nav></section><section class="section"><div class="faq"><details open><summary>揮汗有禮可以換什麼？</summary><p>每個合作通路的商品不同。這個工具的重點不是再做一張很長的清單，而是讓你直接掃手上的商品條碼，一次看哪些通路有可兌換品項。</p></details><details><summary>茶葉蛋、地瓜沒有條碼怎麼辦？</summary><p>直接點上方常見商品或搜尋品名。結果頁會把各通路的官方品名直接列出，不需要跳去官網自己找。</p></details><details><summary>這是官方網站嗎？</summary><p>不是。本站是非官方整理工具，資料可能有遺漏或誤植。實際兌換請以運動部官方最新公告及門市 POS 為準。</p></details></div></section>{footer()}</main>'''
(PUB/'index.html').write_text(layout('揮汗有禮可換什麼？掃條碼查2026兌換商品｜7-11、全家、萊爾富、全聯','2026 揮汗有禮非官方商品查詢工具。直接掃商品條碼，一次確認 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康哪些通路有可兌換品項；茶葉蛋、地瓜等無條碼商品也能直接查。','/',body,[home_schema,faq_schema],'<script src="/assets/data.js"></script><script src="/assets/app.js" defer></script>'),encoding='utf-8')

scanner_body=f'''<main class="wrap scanner-page"><a class="back" href="/">← 回到商品查詢</a><header class="mast"><div class="section-kicker">BARCODE SCANNER</div><h1>對準條碼，<span class="marker">嗶一下</span></h1><p class="lead">掃到商品後，直接一次看六大通路的兌換狀態。</p></header><div class="camera-shell"><video muted playsinline></video><div class="camera-frame"><span></span></div><div class="camera-status" data-camera-status>正在啟動相機…</div></div><div class="manual"><b>掃不到？手動輸入 13 碼條碼</b><form data-manual-form><input data-manual-input inputmode="numeric" maxlength="13" placeholder="例如 4716426880619"><button>查詢</button></form><p class="error" data-manual-error></p></div><div class="disclaimer"><strong>非官方查詢工具</strong><br>掃描結果依本站整理資料判定，可能有遺漏或誤植；實際可兌換商品以官方公告及門市 POS 為準。</div>{footer()}</main>'''
(PUB/'scan/index.html').write_text(layout('揮汗有禮掃條碼查商品｜2026 兌換商品掃描器','直接用手機相機掃商品 EAN-13 條碼，查詢揮汗有禮六大合作通路兌換狀態。非官方工具，結果以官方與門市 POS 為準。','/scan/',scanner_body,None,'<script src="https://unpkg.com/@zxing/browser@0.2.1"></script><script src="/assets/scanner.js" defer></script>'),encoding='utf-8')

lookup_body=f'''<main class="wrap product-page"><a class="back" href="/scan/">← 再掃一個</a><div data-lookup-root><div class="receipt"><b>正在查詢商品…</b></div></div>{footer()}</main>'''
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
    body=f'''<main class="wrap product-page"><a class="back" href="/">← 回到掃碼查詢</a><header class="mast"><div class="section-kicker">揮汗有禮商品查詢</div><h1>{e(p['name'])}<br><span class="marker">哪裡可以換？</span></h1><p class="lead">沒有固定條碼也不用一間一間翻清單。下面直接列各通路目前整理到的官方品名／開放品類。</p></header><div class="receipt"><div class="receipt-top"><div><span class="stamp">{eligible} 個通路有可兌換品項</span><div class="receipt-meta" style="margin-top:10px">最後整理：{CAT['updatedAt']}</div></div></div><div class="store-results">{''.join(rows)}</div></div>{('<div class="disclaimer"><strong>品項提醒</strong><br>'+e(p.get('note',''))+'</div>') if p.get('note') else ''}<div class="disclaimer"><strong>本站不是官方網站</strong><br>資料可能有遺漏或誤植，實際商品、規格、庫存及結帳結果請以運動部官方最新公告與門市 POS 為準。</div>{footer()}</main>'''
    out=PUB/'product'/p['id']/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(layout(title,desc,f'/product/{p["id"]}/',body,schema),encoding='utf-8')

for k,s in CAT['stores'].items():
    slug=s['slug']; d=PUB/slug; d.mkdir(parents=True,exist_ok=True)
    matches=[]
    for p in CAT['products']:
        rec=p['stores'].get(k,{'status':'unknown'})
        if rec['status'] in ('exact','category'):
            href=f'/lookup/?barcode={p["barcode"]}' if p.get('barcode') else f'/product/{p["id"]}/'
            matches.append((p,rec,href))
    rows=''.join(f'<div class="mini-row"><a href="{href}">{e(p["name"])}</a><small>{"官方品項明列" if rec["status"]=="exact" else "官方品類"}</small></div>' for p,rec,href in matches[:30])
    title=f'揮汗有禮 {s["name"]} 可換什麼？2026 兌換商品查詢＋掃碼確認'
    desc=f'2026 揮汗有禮 {s["name"]} 可兌換商品非官方整理。可直接查看常見品項，或回首頁用手機掃條碼確認其他合作通路是否也能兌換。'
    body=f'''<main class="wrap store-page"><a class="back" href="/">← 回到掃碼查詢</a><header class="mast"><div class="section-kicker">2026 揮汗有禮</div><h1>{e(s['name'])}<br><span class="marker">可換什麼？</span></h1><p class="lead">這頁整理本站目前已核對的常見品項。真正方便的方式還是拿起商品直接掃條碼，一次看六大通路。</p><a class="primary" href="/scan/">▥ 掃商品條碼</a></header><section class="section"><div class="section-head"><div><div class="section-kicker">KNOWN ITEMS</div><h2>目前已整理品項</h2></div><a class="source" href="{e(s['source'])}" target="_blank" rel="noreferrer">官方清單 ↗</a></div><div class="mini-table">{rows or '<div class="mini-row"><b>資料整理中</b><small>請以官方為準</small></div>'}</div><p class="micro">這不是完整官方清單，只列本站目前已整理／可查的品項；官方清單可能更多。</p></section><div class="disclaimer"><strong>非官方整理</strong><br>本頁可能有遺漏或誤植，實際兌換資格、商品規格與門市供應請以官方最新公告與 POS 為準。</div>{footer()}</main>'''
    (d/'index.html').write_text(layout(title,desc,f'/{slug}/',body,{"@context":"https://schema.org","@type":"WebPage","name":title,"url":f'{BASE}/{slug}/'}),encoding='utf-8')

urls=['/','/scan/']+[f'/{s["slug"]}/' for s in CAT['stores'].values()]+[f'/product/{p["id"]}/' for p in quick]
(PUB/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n',encoding='utf-8')
(PUB/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{u}</loc><lastmod>{CAT["updatedAt"]}</lastmod></url>' for u in urls)+'\n</urlset>',encoding='utf-8')
(PUB/'manifest.webmanifest').write_text(json.dumps({"name":"揮汗有禮掃碼查詢","short_name":"揮汗掃碼","start_url":"/","display":"standalone","background_color":"#f6f0df","theme_color":"#b6f23a"},ensure_ascii=False),encoding='utf-8')
print('built',len(urls),'indexable URLs')
