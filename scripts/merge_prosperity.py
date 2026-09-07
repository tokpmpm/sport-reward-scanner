import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUB = ROOT / 'public'


def find_store_block(text, heading):
    marker = f'<h3>{heading}</h3>'
    pos = text.find(marker)
    if pos < 0:
        return None
    start = text.rfind('<div class="store-result">', 0, pos)
    if start < 0:
        return None
    depth = 0
    for m in re.finditer(r'<div\b[^>]*>|</div>', text[start:]):
        token = m.group(0)
        depth += 1 if token.startswith('<div') and not token.startswith('</div') else -1
        if depth == 0:
            return start, start + m.end()
    return None


def merge_product_page(path):
    text = path.read_text(encoding='utf-8')
    w = find_store_block(text, '萬家福')
    l = find_store_block(text, '樂家康')
    if not w or not l:
        return

    w_block = text[w[0]:w[1]]
    eligible = ('status yes' in w_block) or ('status category' in w_block)

    # Rename the first shared result and remove the duplicate second result.
    text = text[:w[0]] + w_block.replace('<h3>萬家福</h3>', '<h3>萬家福／樂家康</h3>') + text[w[1]:]
    l = find_store_block(text, '樂家康')
    if l:
        text = text[:l[0]] + text[l[1]:]

    if eligible:
        text = re.sub(
            r'<div class="manual-summary"><span>(\d+) 個通路可確認</span>',
            lambda m: f'<div class="manual-summary"><span>{max(0, int(m.group(1)) - 1)} 個通路可確認</span>',
            text,
            count=1,
        )
    text = text.replace('六大通路', '合作通路')
    path.write_text(text, encoding='utf-8')


# Runtime store metadata: treat 萬家福／樂家康 as one shared channel.
data_path = PUB / 'assets' / 'data.js'
raw = data_path.read_text(encoding='utf-8')
prefix = 'window.SPORT_DATA='
assert raw.startswith(prefix) and raw.endswith(';')
data = json.loads(raw[len(prefix):-1])
wan = data['stores']['wanjiafu']
wan['name'] = '萬家福／樂家康'
wan['short'] = '萬家福／樂家康'
data['stores'].pop('lejiakang', None)
data_path.write_text(prefix + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';', encoding='utf-8')

# Homepage: one shared channel card and neutral wording.
home_path = PUB / 'index.html'
home = home_path.read_text(encoding='utf-8')
home = home.replace('一次查看 7-ELEVEN、全家、萊爾富、全聯、萬家福、樂家康的官方可兌換清單。',
                    '一次查看 7-ELEVEN、全家、萊爾富、全聯、萬家福／樂家康的官方可兌換清單。')
home = home.replace('<h2>六大通路完整商品清單</h2>', '<h2>合作通路完整商品清單</h2>')
chip_pattern = re.compile(
    r'<a class="store-tag store-tag-link" href="/wanjiafu/"[^>]*><span>萬家福</span><span aria-hidden="true">→</span></a>'
    r'<a class="store-tag store-tag-link" href="/lejiakang/"[^>]*><span>樂家康</span><span aria-hidden="true">→</span></a>'
)
home = chip_pattern.sub(
    '<a class="store-tag store-tag-link" href="/wanjiafu/" aria-label="查看 萬家福／樂家康 完整可兌換商品清單"><span>萬家福／樂家康</span><span aria-hidden="true">→</span></a>',
    home,
)
home_path.write_text(home, encoding='utf-8')

# Manual product pages: collapse the two identical result rows into one.
for p in (PUB / 'product').glob('*/index.html'):
    merge_product_page(p)

# Shared catalog page uses the existing /wanjiafu/ URL.
wan_path = PUB / 'wanjiafu' / 'index.html'
if wan_path.exists():
    text = wan_path.read_text(encoding='utf-8')
    text = text.replace('萬家福', '萬家福／樂家康')
    wan_path.write_text(text, encoding='utf-8')

# Keep old /lejiakang/ links working, but make them a redirect rather than a duplicate catalog.
lej_dir = PUB / 'lejiakang'
lej_dir.mkdir(parents=True, exist_ok=True)
(lej_dir / 'index.html').write_text('''<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://sport.meshthings.com/wanjiafu/"><meta http-equiv="refresh" content="0;url=/wanjiafu/"><title>萬家福／樂家康｜揮汗有禮</title></head><body><p>萬家福與樂家康共用同一份活動商品清單，正在前往<a href="/wanjiafu/">萬家福／樂家康</a>。</p></body></html>''', encoding='utf-8')

# Replace duplicated footer links everywhere.
for p in PUB.rglob('*.html'):
    text = p.read_text(encoding='utf-8')
    text = text.replace('<a href="/wanjiafu/">萬家福</a><a href="/lejiakang/">樂家康</a>',
                        '<a href="/wanjiafu/">萬家福／樂家康</a>')
    p.write_text(text, encoding='utf-8')

# The duplicate route is not indexable and should not appear in sitemap.
sitemap = PUB / 'sitemap.xml'
if sitemap.exists():
    text = sitemap.read_text(encoding='utf-8')
    text = re.sub(r'<url><loc>https://sport\.meshthings\.com/lejiakang/</loc><lastmod>[^<]+</lastmod></url>', '', text)
    sitemap.write_text(text, encoding='utf-8')

# Guardrails.
assert 'lejiakang' not in data['stores']
assert data['stores']['wanjiafu']['name'] == '萬家福／樂家康'
assert '<span>樂家康</span>' not in home_path.read_text(encoding='utf-8')
assert '/lejiakang/</loc>' not in sitemap.read_text(encoding='utf-8')
for p in (PUB / 'product').glob('*/index.html'):
    assert '<h3>樂家康</h3>' not in p.read_text(encoding='utf-8')

print('CHANNEL MERGE PASSED: 萬家福／樂家康 displayed as one shared channel')
