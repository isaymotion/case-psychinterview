import sys, json, os, base64; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8817)
data=json.load(open(fx)); errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1180,'height':820})
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8817/index.html'); pg.wait_for_timeout(300)
    res = pg.evaluate("""async (d)=>{
      const out={}; const b64=u=>{ let s=''; for(let i=0;i<u.length;i+=0x8000) s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000)); return btoa(s); };
      for(const t of CaseSlides.TEMPLATES){
        const buf = await (await fetch(t.file)).arrayBuffer();
        const avail = CaseSlides.availableSections(d, SECTIONS).map(x=>x.id);
        const r = await CaseSlides.generate(d, { template:buf, templateCfg:t, title:d.caseTitle, presenter:d.preparedBy, patientAs:'initials', dividers:true, notes:true, include:avail });
        let pdf=null; if(t.pdf) pdf = b64(await CasePDF.render(r.deck, { backgrounds:t.pdf.backgrounds, fonts:'fonts/', title:'x' }));
        out[t.id] = { count:r.count, pptx:b64(r.bytes), pdf, avail };
      }
      return out; }""", data)
    for k,v in res.items():
        open(os.path.join(out, f'slides_{k}.pptx'),'wb').write(base64.b64decode(v['pptx']))
        if v['pdf']: open(os.path.join(out, f'slides_{k}.pdf'),'wb').write(base64.b64decode(v['pdf']))
        print(k, v['count'], 'slides', '| pdf' if v['pdf'] else '')
    print('sections offered:', res['colorful']['avail'])
    b.close()
print('errors', errs)
