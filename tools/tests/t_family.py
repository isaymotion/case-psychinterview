# Family editor and genogram, end to end: python3 t_family.py <tests> <app> <out>
# Builds the sample family by hand in the app, checks what is saved, exports Word (both layouts) and reopens it,
# then makes slides + PDF for the large fixture family.
import sys, json, os, base64; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
T, root, out = sys.argv[1], sys.argv[2], sys.argv[3]; start(root, 8823)
fams = json.load(open(os.path.join(T,'fixtures/families.json'))); errs=[]
def ok(c, m):
    if not c: errs.append(m)
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1180,'height':820}, accept_downloads=True, has_touch=True)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8823/index.html'); pg.wait_for_timeout(300)
    pg.click('#new'); pg.wait_for_timeout(200)
    pg.fill('[data-f="patient"]','Santos, Mark D.'); pg.fill('[data-f="agesex"]','33 / M')
    secs = pg.evaluate("Array.from(document.querySelectorAll('#rail [data-sec]')).map(b=>b.textContent.replace(/\\s+/g,' ').trim())")
    i13=[k for k,t in enumerate(secs) if t.startswith('13')][0]; pg.click(f'#rail [data-sec="{i13}"]'); pg.wait_for_timeout(150)
    pg.fill('[data-geno="genoPtName"]','Mark'); pg.fill('[data-geno="genoPtOcc"]','BS ME graduate'); pg.fill('[data-geno="genoPtCond"]','Schizophrenia; AUD, TUD (severe); CKD 3b')
    # typed youngest first on purpose
    rows=[('', 'Child (sex not stated)', '', {'count':'7','occ':'high school to elementary age; video calls only'}),
          ('', 'Former partner', '', {'count':'5','sex':'Female'}),
          ('Edna','Sister','28',{'occ':'only sibling','cond':'Works at NGCP'}),
          ('Carla','Mother','58',{'occ':'housewife, caregiver','cond':'Diabetes on insulin'}),
          ('Gregorio','Father','57',{'occ':'welder, sole earner','cond':'Uncontrolled hypertension'})]
    for i,(n,r,a,ex) in enumerate(rows):
        pg.click('[data-famadd]'); pg.select_option(f'[data-fam="{i}"][data-fk="rel"]', r); pg.fill(f'[data-fam="{i}"][data-fk="name"]', n); pg.fill(f'[data-fam="{i}"][data-fk="age"]', a)
        for k,v in ex.items():
            sel=f'[data-fam="{i}"][data-fk="{k}"]'
            if k=='sex': pg.select_option(sel, v)
            else: pg.fill(sel, v)
    pg.click('[data-famtog="3"][data-fk="withPt"]'); pg.click('[data-famtog="4"][data-fk="withPt"]')
    pg.select_option('select[data-f="parentsRel"]', 'Married')   # a grouped picker since v37 (was buttons)
    ids = pg.evaluate("Object.values(JSON.parse(localStorage.getItem('psyCaseApp.v1')||'{}').cases||{}).length")
    pg.wait_for_timeout(700)
    fam = lambda: pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); return Object.values(s.cases)[0].data})()")
    d=fam(); idof={m['rel']:m['id'] for m in d['family']}
    ok(all(m.get('id') for m in d['family']) and len(set(idof.values()))==5, 'ids missing')
    for j,(a_,t,b_) in enumerate([('pt','Close but conflictual','Father'),('pt','Very close / enmeshed','Mother'),('pt','Distant','Sister'),('pt','Cut off / estranged','Former partner')]):
        pg.click('[data-linkadd]'); pg.select_option(f'[data-link="{j}"][data-lk="type"]', t); pg.select_option(f'[data-link="{j}"][data-lk="b"]', idof[b_])
    pg.click('[data-famsort]'); pg.wait_for_timeout(700)
    d=fam(); order=[m['rel'] for m in d['family']]
    print('after sort:', order); ok(order==['Father','Mother','Sister','Former partner','Child (sex not stated)'], 'sort order '+str(order))
    ok(len(d['famLinks'])==4 and d['famLinks'][0]['b']==idof['Father'], 'links lost after sort')
    # move down then up leaves the list as it was
    pg.click('[data-fammove="0"][data-dir="1"]'); pg.click('[data-fammove="1"][data-dir="-1"]'); pg.wait_for_timeout(600)
    ok([m['rel'] for m in fam()['family']]==order, 'move up/down')
    svg=pg.inner_html('#geno'); ok('5 former partners' in svg and '7 children' in svg and 'Close but conflictual' in svg and 'Index patient' in svg, 'genogram text')
    pg.wait_for_timeout(300); pg.locator('#geno').scroll_into_view_if_needed(); pg.screenshot(path=out+'/fam-ui.png', full_page=True)
    with pg.expect_download() as dl: pg.click('[data-genosave]')
    dl.value.save_as(os.path.join(out,'fam_genogram.png')); print('picture:', dl.value.suggested_filename)
    # removing a person removes the lines that point at them
    pg.once('dialog', lambda x: x.accept()); pg.click('[data-famdel="2"]'); pg.wait_for_timeout(600)
    ok(len(fam()['famLinks'])==3, 'link to a removed person stayed')
    # Word: both layouts, then reopen
    def export(tag):
        for lay in ['protocol','form']:
            pg.click('#export'); pg.wait_for_selector(f'[data-lay="{lay}"]'); pg.click(f'[data-lay="{lay}"]'); pg.wait_for_selector('#wshare', timeout=15000)
            with pg.expect_download() as dl: pg.click('#wshare')
            dl.value.save_as(os.path.join(out, f'fam_{tag}_{lay}.docx')); pg.click('[data-close]')
    export('sample')
    back = pg.evaluate("""async (b64)=>{ const u=Uint8Array.from(atob(b64), c=>c.charCodeAt(0)); const r=await DocxImport.fileToData(new File([u],'x.docx')); return { fam:r.data.family, links:r.data.famLinks, pt:r.data.genoPtName, edited:r.edited }; }""",
        base64.b64encode(open(os.path.join(out,'fam_sample_form.docx'),'rb').read()).decode())
    ok(back['pt']=='Mark' and len(back['links'])==3 and back['fam'][3].get('count')=='7', 'reopened Word file lost genogram details: '+json.dumps(back)[:300])
    # the large family: Word + slides + PDF
    big=dict(fams['big']); big.update({'patient':'Dela Cruz, Juana R.','caseTitle':'Genogram test','preparedBy':'Tester'})
    pg.close(); pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8823/index.html'); pg.wait_for_timeout(300)   # a fresh page: the app saves the open record when a page closes
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", big)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]'); pg.wait_for_timeout(200)
    export('big')
    res = pg.evaluate("""async (d)=>{ const b64=u=>{ let s=''; for(let i=0;i<u.length;i+=0x8000) s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000)); return btoa(s); };
      const t=CaseSlides.TEMPLATES[0], buf=await (await fetch(t.file)).arrayBuffer();
      const r = await CaseSlides.generate(d, { template:buf, templateCfg:t, textScale:1.3, title:d.caseTitle, presenter:d.preparedBy, patientAs:'initials', dividers:false, notes:true, include:['famprof'] });
      const pdf = t.pdf ? b64(await CasePDF.render(r.deck, { backgrounds:t.pdf.backgrounds, fonts:'fonts/', title:'x' })) : null;
      return { count:r.count, pptx:b64(r.bytes), pdf }; }""", big)
    open(os.path.join(out,'fam_slides.pptx'),'wb').write(base64.b64decode(res['pptx']))
    if res['pdf']: open(os.path.join(out,'fam_slides.pdf'),'wb').write(base64.b64decode(res['pdf']))
    print('slides:', res['count'])
    b.close()
print('errors', errs)
