import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUB = ROOT / 'public'
DATA = json.loads((ROOT / 'data' / 'recommendations.json').read_text(encoding='utf-8'))


def e(value):
    return html.escape(str(value), quote=True)


allowance_by_store = {x['store']: int(x['amount']) for x in DATA['allowances']}
errors = []
for item in DATA['items']:
    allowance = int(item['allowance'])
    total = int(item['total'])
    extra = int(item['extra'])
    if item['store'] not in allowance_by_store:
        errors.append(f"unknown store: {item['store']}")
    elif allowance_by_store[item['store']] != allowance:
        errors.append(f"allowance mismatch: {item['id']}")
    if total - allowance != extra:
        errors.append(f"extra mismatch: {item['id']} ({total}-{allowance}!={extra})")
    if extra < 0:
        errors.append(f"negative extra: {item['id']}")

if errors:
    raise SystemExit('RECOMMENDATION QA FAILED:\n- ' + '\n- '.join(errors))

items = sorted(DATA['items'], key=lambda x: (int(x['extra']), x['store'], x['title']))

allowance_html = ''.join(
    f'<span class="allowance-chip" title="{e(x["note"])}">{e(x["store"])} <strong>{int(x["amount"])} 元</strong></span>'
    for x in DATA['allowances']
)

store_order = ['seven', 'family', 'hilife', 'pxmart', 'prosperity']
store_labels = {
    'seven': '7-ELEVEN',
    'family': '全家',
    'hilife': '萊爾富',
    'pxmart': '全聯',
    'prosperity': '萬家福／樂家康',
}
present = {x['storeKey'] for x in items}
filter_html = '<button class="recommendation-filter" type="button" data-recommendation-filter="all" aria-pressed="true">補最少</button>'
filter_html += ''.join(
    f'<button class="recommendation-filter" type="button" data-recommendation-filter="{e(key)}" aria-pressed="false">{e(store_labels[key])}</button>'
    for key in store_order if key in present
)

cards = []
for item in items:
    extra = int(item['extra'])
    extra_label = '0 元' if extra == 0 else f'+{extra} 元'
    extra_class = ' zero' if extra == 0 else ''
    lines = ''.join(f'<div>・{e(line)}</div>' for line in item['lines'])
    cards.append(
        f'''<article class="recommendation-card" data-recommendation-card data-id="{e(item['id'])}" data-store="{e(item['storeKey'])}" data-store-name="{e(item['store'])}" data-title="{e(item['title'])}" data-extra="{extra}">
<div class="recommendation-top"><span class="recommendation-store">{e(item['store'])}</span><span class="recommendation-extra{extra_class}"><strong>{extra_label}</strong><br>{'剛好折完' if extra == 0 else '補差額'}</span></div>
<div class="recommendation-emoji" aria-hidden="true">{e(item['emoji'])}</div>
<h3>{e(item['title'])}</h3>
<div class="recommendation-lines">{lines}</div>
<div class="recommendation-money"><span>可折額度<b>{int(item['allowance'])} 元</b></span><span>商品總額<b>{int(item['total'])} 元</b></span></div>
<a class="recommendation-link" data-recommendation-link href="{e(item['link'])}">{e(item['linkLabel'])} →</a>
</article>'''
    )

section = f'''<section class="recommendation-section" data-recommendations>
<div class="section-head"><div><div class="section-kicker">COMMUNITY PICKS</div><h2>50 元怎麼換最划算？</h2></div><span class="micro">部分通路有加碼</span></div>
<p class="recommendation-intro">網友實際兌換組合，直接看要補多少。7-ELEVEN、全家可用 55 元，萊爾富可用 60 元。</p>
<div class="allowance-strip" aria-label="各通路可折額度">{allowance_html}</div>
<div class="recommendation-filters" aria-label="篩選推薦通路">{filter_html}</div>
<div class="recommendation-grid">{''.join(cards)}</div>
<div class="recommendation-empty" data-recommendation-empty>目前這個通路還沒有網友推薦組合。</div>
<p class="recommendation-note">網友回報整理（{e(DATA['updatedAt'])}）。價格、促銷、庫存與門市狀況可能不同，實際可兌換品項與補差額仍以官方公告及現場 POS 為準。</p>
</section>'''

index = PUB / 'index.html'
text = index.read_text(encoding='utf-8')
marker = '<section class="section"><div class="section-head"><div><div class="section-kicker">STORE CATALOGS</div>'
if marker not in text:
    raise SystemExit('RECOMMENDATION BUILD FAILED: STORE CATALOGS marker not found')
text = text.replace(marker, section + marker, 1)

css = '<link rel="stylesheet" href="/assets/recommendations.css">'
if css not in text:
    text = text.replace('</head>', css + '</head>', 1)
js = '<script src="/assets/recommendations.js" defer></script>'
if js not in text:
    text = text.replace('</body>', js + '</body>', 1)
index.write_text(text, encoding='utf-8')

print(f'RECOMMENDATION QA PASSED {len(items)} items')
