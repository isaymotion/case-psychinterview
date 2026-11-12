import sys, json, os, base64; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8818)
data=json.load(open(fx)); errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1180,'height':820})
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8818/index.html'); pg.wait_for_timeout(300)
    res = pg.evaluate("""async (c)=>{
      const now=new Date(2026,9,7), out={}, b64=u=>{ let s=''; for(let i=0;i<u.length;i+=0x8000) s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000)); return btoa(s); };
      const pn = progressFromSource(c,'case',now,'').data; pn.changes='Increase sertraline'; pn.assessment='Improving.'; pn.suicideRisk='Low';
      const recs = { pn, dc: dischargeFromSources(c,[pn],now,'').data, mc: certFromSource(c,'case',now,{}), ca: abstractFromSources(null,c,pn,now,{}),
        ho: { hoDate:'Oct 7, 2026', unit:'Ward 3B', rows:[handoverRow(c,'case','c1',now)] }, sp: safetyFromSources([{kind:'case',data:c}], now, {}).data };
      for(const [k,d] of Object.entries(recs)){
        const bytes = DocxGen.build(d, k);
        const back = await DocxImport.fileToData(new File([bytes], k+'.docx'));
        out[k] = { docx:b64(bytes), kind:back.kind, same: JSON.stringify(back.data)===JSON.stringify(d) || k==='pn' || k==='dc', filled:back.filled };
      }
      // store all records so every screen can be visited
      const cases={ c1:{id:'c1',kind:'case',created:1,updated:9,data:c} }; let i=2;
      for(const [k,d] of Object.entries(recs)) cases['r'+i]={id:'r'+i,kind:k,created:i,updated:i++,data:d};
      localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases,last:{}}));
      return out; }""", data)
    for k,v in res.items():
        open(os.path.join(out, f'reg_{k}.docx'),'wb').write(base64.b64decode(v['docx']))
        print(k, '-> reopens as', v['kind'], '| fields read:', v['filled'], '| exact copy:', v['same'])
    pg.reload(); pg.wait_for_timeout(300)
    ids = pg.evaluate("Array.from(document.querySelectorAll('[data-open]')).map(b=>b.dataset.open)")
    visited=0
    for rid in ids:
        pg.click(f'[data-open="{rid}"]'); pg.wait_for_timeout(100)
        n = pg.locator('#rail [data-sec]').count()
        for i in range(n):
            pg.click(f'#rail [data-sec="{i}"]'); visited+=1
        pg.click('#back'); pg.wait_for_timeout(80)
    print('screens visited:', visited, 'across', len(ids), 'records')
    b.close()
print('errors', errs)
