# Export from one app version, open in the new app, compare stored data
import sys, json, os, shutil, zipfile, re; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
scripts, work, live, fx = sys.argv[1:5]
start(work, 8813); start(live, 8814)
data = json.load(open(os.path.join(fx,'case_full.json')))
errs=[]
def clean(v):
    if isinstance(v,list):
        if v and isinstance(v[0],list): return [r for r in v if any(str(c).strip() for c in r)]
        if v and isinstance(v[0],dict): return v
        return [x for x in v if str(x).strip()]
    if isinstance(v,dict): return {k:x for k,x in v.items() if x not in ('',None)}
    return v
def diff(a,b):
    out=[]
    for k,v in a.items():
        if clean(v) in (None,'',[],{}): continue
        if clean(v)!=clean(b.get(k)): out.append(k)
    return out
def open_in_app(pg, port, f):
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(200)
    pg.click('#imp'); pg.set_input_files('#impFile', f); pg.wait_for_selector('[data-close]', timeout=15000)
    warn = pg.locator('.warn-box').count()>0
    missed = pg.locator('.sheet li').all_inner_texts()
    st=pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1'))"); rec=sorted(st['cases'].values(), key=lambda c:-c['created'])[0]
    return rec, warn, missed
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1180,'height':820}, accept_downloads=True)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    # 1-2: new exports, unchanged
    for lay in ['protocol','form']:
        rec,warn,missed = open_in_app(pg, 8813, os.path.join(fx, f'case_{lay}.docx'))
        print(lay, 'unchanged -> kind', rec['kind'], '| differences:', diff(data, rec['data']) or 'none', '| warning:', warn)
    # 3: app-format file edited in Word
    import docx
    doc = docx.Document(os.path.join(fx,'case_form.docx'))
    for t in doc.tables:
        for r in t.rows:
            if r.cells[0].text.strip()=='Onset of illness': r.cells[1].paragraphs[0].runs[0].text='3 months prior to admission'
            if r.cells[0].text.strip()=='Name' : pass
        if t.rows[0].cells[0].text.strip()=='Name' and t.rows[0].cells[1].text.strip()=='Relationship':
            t.rows[2].cells[5].paragraphs[0].add_run('Visits weekly.')
        if t.rows[0].cells[0].text.strip()=='Panel':
            for r in t.rows:
                if r.cells[1].text.strip()=='Sodium': r.cells[2].paragraphs[0].runs[0].text='131'
    doc.save(os.path.join(fx,'case_form_edited.docx'))
    rec,warn,missed = open_in_app(pg, 8813, os.path.join(fx,'case_form_edited.docx'))
    d=rec['data']
    print('form edited in Word -> onset:', d.get('onset'), '| mother desc:', d['family'][1].get('desc'), '| sodium:', [r for r in d['labPanels']['lytes'] if r[0]=='Sodium'], '| other differences:', [k for k in diff(data,d) if k not in ('onset','family','labPanels')] or 'none', '| warning:', warn, '| unplaced:', missed[:5])
    # 4: protocol edited in Word
    doc = docx.Document(os.path.join(fx,'case_protocol.docx')); doc.paragraphs[-1].add_run(' (edited)'); doc.save(os.path.join(fx,'case_protocol_edited.docx'))
    rec,warn,missed = open_in_app(pg, 8813, os.path.join(fx,'case_protocol_edited.docx'))
    print('protocol edited in Word -> warning shown:', warn, '| data intact:', not diff(data, rec['data']))
    # 5: file exported by the current live app (old layout)
    old = {k:v for k,v in data.items()}
    pg.goto('http://127.0.0.1:8814/index.html'); pg.evaluate("localStorage.clear()")
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", old)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]'); pg.wait_for_timeout(200)
    with pg.expect_download() as dl: pg.click('#export')
    dl.value.save_as(os.path.join(fx,'case_oldapp.docx'))
    rec,warn,missed = open_in_app(pg, 8813, os.path.join(fx,'case_oldapp.docx'))
    # fields the old app knew about
    oldF = set(re.findall(r"id:'(\w+)'", open(os.path.join(live,'index.html'),encoding='utf-8').read().split('const SECTIONS = [')[1].split('const REMINDERS')[0]))
    known = {k:v for k,v in old.items() if k in oldF}
    print('old-app Word file -> differences:', diff(known, rec['data']) or 'none', '| unplaced:', missed[:6])
    b.close()
print('errors', errs)
