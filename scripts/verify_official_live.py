import json, pathlib, re, sys, urllib.request, unicodedata
from collections import Counter
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/official-catalog.json').read_text(encoding='utf-8'))
LOCAL={k:json.loads((ROOT/rel).read_text(encoding='utf-8')) for k,rel in MANIFEST['stores'].items()}


def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def canon_label(s): return unicodedata.normalize('NFKC',clean(s))
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 SportRewardScannerQA/1.0','Accept-Language':'zh-TW,zh;q=0.9'})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read().decode('utf-8','replace')

def group_items(soup,label,expected):
    candidates=[]
    for tag in soup.find_all(True):
        text=clean(tag.get_text(' ',strip=True))
        if label not in text or str(expected) not in text or '項' not in text: continue
        lis=[clean(li.get_text(' ',strip=True)) for li in tag.find_all('li')]
        if len(lis)==expected: candidates.append((len(text),lis,tag.name))
    if not candidates:
        for node in soup.find_all(string=lambda x: x and label in clean(x)):
            cur=node.parent
            for _ in range(10):
                if not cur: break
                lis=[clean(li.get_text(' ',strip=True)) for li in cur.find_all('li')]
                if len(lis)==expected:
                    candidates.append((len(clean(cur.get_text(' ',strip=True))),lis,cur.name));break
                cur=cur.parent
    if not candidates: raise AssertionError(f'cannot parse group: {label} / expected {expected}')
    candidates.sort(key=lambda x:x[0]);return candidates[0][1]

def first_unique(rows):
    seen=set();out=[]
    for x in rows:
        if x not in seen: seen.add(x);out.append(x)
    return out

def compare_sequence(label,live,local,errors,ignore_order=False):
    same=Counter(live)==Counter(local) if ignore_order else live==local
    if same:return
    live_c,local_c=Counter(live),Counter(local)
    missing=list((live_c-local_c).elements());extra=list((local_c-live_c).elements())
    errors.append({'scope':label,'missing':missing[:50],'extra':extra[:50],'liveCount':len(live),'localCount':len(local),'orderOnly':not missing and not extra})

def parse_rule_table(soup):
    rows=[]
    for tr in soup.find_all('tr'):
        cells=[clean(x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
        if len(cells)<2: continue
        if cells[0] in ('分類','類別名稱') or '商品名稱' in cells[1]: continue
        if cells[0] and cells[1]: rows.append((cells[0],cells[1]))
    return rows

def parse_family_categories(soup):
    result=[]
    for card in soup.select('details.category-card'):
        classes=set(card.get('class') or [])
        if 'all-items' in classes: continue
        title_node=card.select_one('.category-title')
        if not title_node: continue
        title=clean(title_node.get_text(' ',strip=True))
        m=re.match(r'^(.*?)\s+(\d+)\s*項$',title)
        if not m: raise AssertionError(f'cannot parse Family category title: {title}')
        name=clean(m.group(1));declared=int(m.group(2))
        items=[clean(li.get_text(' ',strip=True)) for li in card.find_all('li')]
        if len(items)!=declared:
            raise AssertionError(f'Family live category count mismatch: {name} {len(items)}/{declared}')
        result.append({'name':name,'count':declared,'items':items})
    return result

def verify_family_categories(store,soup,errors):
    live_cards=parse_family_categories(soup);local_categories=store.get('categories',[])
    live_names=[canon_label(c['name']) for c in live_cards];local_names=[canon_label(c['name']) for c in local_categories]
    if live_names!=local_names:
        live_c,local_c=Counter(live_names),Counter(local_names)
        missing=list((live_c-local_c).elements());extra=list((local_c-live_c).elements())
        errors.append({'scope':'family/category-names','missing':missing[:50],'extra':extra[:50],'liveCount':len(live_names),'localCount':len(local_names),'orderOnly':not missing and not extra})
    reports=[];local_by_name={canon_label(c['name']):c for c in local_categories}
    for live in live_cards:
        local=local_by_name.get(canon_label(live['name']))
        if not local:
            reports.append({'name':live['name'],'live':live['count'],'local':None,'pass':False});continue
        local_items=[clean(x) for x in local.get('items',[])]
        if live['count']!=local['officialCount']:
            errors.append({'scope':f'family/{live["name"]}/declared-count','missing':[],'extra':[],'liveCount':live['count'],'localCount':local['officialCount'],'orderOnly':False})
        # Item names stay exact: no Unicode normalization here.
        compare_sequence(f'family/{live["name"]}',live['items'],local_items,errors)
        reports.append({'name':live['name'],'localName':local['name'],'labelNFKCEquivalent':canon_label(live['name'])==canon_label(local['name']),'live':len(live['items']),'local':len(local_items),'pass':live['items']==local_items and live['count']==local['officialCount']})
    return reports

def verify_fixed(key,store,html,errors,summary):
    soup=BeautifulSoup(html,'html.parser');category_reports=[]
    if key=='family':
        category_reports=verify_family_categories(store,soup,errors)
    else:
        for cat in store.get('categories',[]):
            live=group_items(soup,cat['name'],cat['officialCount']);local=[clean(x) for x in cat.get('items',[])]
            compare_sequence(f'{key}/{cat["name"]}',live,local,errors)
            category_reports.append({'name':cat['name'],'live':len(live),'local':len(local),'pass':live==local})
    for cat in store.get('bonusCategories',[]):
        live=group_items(soup,cat['name'],cat['officialCount']);local=[clean(x) for x in cat.get('items',[])]
        compare_sequence(f'{key}/bonus/{cat["name"]}',live,local,errors)
        category_reports.append({'name':'bonus/'+cat['name'],'live':len(live),'local':len(local),'pass':live==local})
    live_all=group_items(soup,'全部品項',store['officialTotal'])
    if key=='family':
        local_all=first_unique([clean(x) for c in store['categories'] for x in c.get('items',[])])
        compare_sequence(f'{key}/all-items',live_all,local_all,errors,ignore_order=True)
        coverage='master list + all category rows'
    else:
        local_all=[clean(x) for c in store['categories'] for x in c.get('items',[])]
        compare_sequence(f'{key}/all-items',live_all,local_all,errors)
        coverage='master list + category rows'
    summary[key]={'mode':store['mode'],'coverage':coverage,'masterLive':len(live_all),'masterLocal':len(local_all),'categories':category_reports,'pass':not any(e['scope'].startswith(key+'/') for e in errors)}

def verify_rules(key,store,html,errors,summary):
    soup=BeautifulSoup(html,'html.parser');live=parse_rule_table(soup);local=[(clean(c['name']),clean(c.get('examples',''))) for c in store['categories']]
    if live!=local:
        live_c,local_c=Counter(live),Counter(local)
        errors.append({'scope':key+'/category-rules','missing':[list(x) for x in (live_c-local_c).elements()][:50],'extra':[list(x) for x in (local_c-live_c).elements()][:50],'liveCount':len(live),'localCount':len(local),'orderOnly':Counter(live)==Counter(local)})
    summary[key]={'mode':store['mode'],'coverage':'category names + examples','liveRows':len(live),'localRows':len(local),'pass':live==local}

def main():
    cache={};errors=[];summary={}
    for key,store in LOCAL.items():
        try:
            url=store['source'];html=cache.setdefault(url,fetch(url))
            if store['mode']=='category_rules': verify_rules(key,store,html,errors,summary)
            else: verify_fixed(key,store,html,errors,summary)
        except Exception as exc:
            errors.append({'scope':key+'/parser','error':str(exc),'missing':[],'extra':[]})
            summary[key]={'mode':store.get('mode'),'pass':False,'parserError':str(exc)}
    report={'pass':not errors,'stores':summary,'errors':errors}
    (ROOT/'live-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('LIVE OFFICIAL DIFF REPORT');print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: sys.exit(1)

if __name__=='__main__': main()
