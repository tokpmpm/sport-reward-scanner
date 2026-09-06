import re, urllib.request
from bs4 import BeautifulSoup

url='https://500.gov.tw/registrant/intro/vendor-1.html'
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 SportRewardScannerQA/1.0'})
html=urllib.request.urlopen(req,timeout=30).read().decode('utf-8','replace')
soup=BeautifulSoup(html,'html.parser')

def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
for label in ['FMC',"Let's Café",'水果','茶葉蛋','健康志向']:
    print('\n===== LABEL',label,'=====')
    nodes=list(soup.find_all(string=lambda x:x and label in clean(x)))[:8]
    print('nodes',len(nodes))
    for n_i,node in enumerate(nodes):
        print('NODE',n_i,repr(clean(node))[:400])
        cur=node.parent
        for level in range(7):
            if not cur:break
            text=clean(cur.get_text(' ',strip=True))
            print('  LEVEL',level,'tag=',cur.name,'class=',cur.get('class'),'id=',cur.get('id'),'li=',len(cur.find_all('li')),'text=',repr(text[:500]))
            cur=cur.parent
