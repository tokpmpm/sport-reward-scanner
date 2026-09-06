import json, pathlib, re, sys, urllib.request
from collections import Counter
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'data/official-catalog.json').read_text(encoding='utf-8'))
LOCAL={k:json.loads((ROOT/rel).read_text(encoding='utf-8')) for k,rel in MANIFEST['stores'].items()}


def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 SportRewardScannerQA/1.0','Accept-Language':'zh-TW,zh;q=0.9'})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read().decode('utf-8','replace')

def group_items(soup,label,expected):
    candidates=[]
    for tag in soup.find_all(True):
        text=clean(tag.get_text(' ',strip=True))
        if label not in text or str(expected) not in text or '項' not in text: continue
        lis=[clean(li.get_text(' ',strip=True)) for li in tag.find_all('li')]
        if len(lis)==expected:
            candidates.append((len(text),lis,tag.name))
    if not candidates:
        # fallback: start from any node containing the label and climb to the smallest ancestor with exactly expected list items
        for node in soup.find_all(string=lambda x: x and label in clean(x)):
            cur=node.parent
            for _ in range(10):
                if not cur: break
                lis=[clean(li.get_text(' ',strip=True)) for li in cur.find_all('li')]
                if len(lis)==expected:
                    candidates.append((len(clean(cur.get_text(' ',strip=True))),lis,cur.name));break
                cur=cur.parent
    if not candidates:
        raise AssertionError(f'cannot parse group: {label} / expected {expected}')
    candidates.sort(key=lambda x:x[0])
    return candidates[0][1]

def first_unique(rows):
    seen=set();out=[]
    for x in rows:
        if x not in seen: seen.add(x);out.append(x)
    return out

def compare_sequence(label,live,local,errors):
    if live==local:return
    live_c,local_c=Counter(live),Counter(local)
    missing=list((live_c-local_c).elements());extra=list((local_c-live_c).elements())
    errors.append({'scope':label,'missing':missing[:30],'extra':extra[:30],'liveCount':len(live),'localCount':len(local),'orderOnly':not missing and not extra})

def parse_rule_table(soup):
    rows=[]
    for tr in soup.find_all('tr'):
        cells=[clean(x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
        if len(cells)<2: continue
        if cells[0] in ('分類','類別名稱') or '商品名稱' in cells[1] or cells[0]=='分類': continue
        if cells[0] and cells[1]: rows.append((cells[0],cells[1]))
    return rows

def verify_fixed(key,store,html,errors,summary):
    soup=BeautifulSoup(html,'html.parser')
    category_reports=[]
    for cat in store.get('categories',[]):
        live=group_items(soup,cat['name'],cat['officialCount'])
        local=[clean(x) for x in cat.get('items',[])]
        compare_sequence(f'{key}/{cat["name"]}',live,local,errors)
        category_reports.append({'name':cat['name'],'live':len(live),'local':len(local),'pass':live==local})
    for cat in store.get('bonusCategories',[]):
        live=group_items(soup,cat['name'],cat['officialCount'])
        local=[clean(x) for x in cat.get('items',[])]
        compare_sequence(f'{key}/bonus/{cat["name"]}',live,local,errors)
        category_reports.append({'name':'bonus/'+cat['name'],'live':len(live),'local':len(local),'pass':live==local})
    if key=='seven':
        live_all=group_items(soup,'全部品項',store['officialTotal'])
        local_all=[clean(x) for c in store['categories'] for x in c.get('items',[])]
        compare_sequence(f'{key}/all-items',live_all,local_all,errors)
    elif key=='family':
        live_all=group_items(soup,'全部品項',store['officialTotal'])
        local_all=first_unique([clean(x) for c in store['categories'] for x in c.get('items',[])])
        if Counter(live_all)!=Counter(local_all):
            compare_sequence(f'{key}/all-items',live_all,local_all,errors)
    elif key=='hilife':
        live_all=group_items(soup,'全部品項',store['officialTotal'])
        local_all=[clean(x) for c in store['categories'] for x in c.get('items',[])]
        compare_sequence(f'{key}/all-items',live_all,local_all,errors)
    summary[key]={'mode':store['mode'],'categories':category_reports,'pass':not any(e['scope'].startswith(key+'/') for e in errors)}

def verify_rules(key,store,html,errors,summary):
    soup=BeautifulSoup(html,'html.parser');live=parse_rule_table(soup)
    local=[(clean(c['name']),clean(c.get('examples',''))) for c in store['categories']]
    if live!=local:
        live_c,local_c=Counter(live),Counter(local)
        errors.append({'scope':key+'/category-rules','missing':[list(x) for x in (live_c-local_c).elements()][:30],'extra':[list(x) for x in (local_c-live_c).elements()][:30],'liveCount':len(live),'localCount':len(local),'orderOnly':Counter(live)==Counter(local)})
    summary[key]={'mode':store['mode'],'liveRows':len(live),'localRows':len(local),'pass':live==local}

def main():
    cache={};errors=[];summary={}
    for key,store in LOCAL.items():
        url=store['source'];html=cache.setdefault(url,fetch(url))
        if store['mode']=='category_rules': verify_rules(key,store,html,errors,summary)
        else: verify_fixed(key,store,html,errors,summary)
    report={'pass':not errors,'stores':summary,'errors':errors}
    out=ROOT/'live-verification.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('LIVE OFFICIAL DIFF REPORT')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: sys.exit(1)

if __name__=='__main__': main()
