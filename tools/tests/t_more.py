# v40: Word export of a case without the name (initials / "Patient A"), backup reminder.
# Usage: python3 t_more.py <tests folder> <app folder> <fixture json> <out folder>
import sys, json, os, zipfile, re; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8828)
data=json.load(open(fx)); errs=[]
def check(ok, msg):
    if not ok: errs.append(msg)
DAY=86400000
SEED = """([c,now])=>{ const D=864e5;
  const cases={ c1:{id:'c1',kind:'case',created:now-20*D,updated:now-2*D,data:c}, c2:{id:'c2',kind:'case',created:now-3*D,updated:now-3*D,data:{patient:'Zeta Testcase',mrn:'99-0042'}} };
  localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases,last:{}})); }"""
U='http://127.0.0.1:8828/index.html'
LAST="JSON.parse(localStorage.getItem('psyCaseApp.v1')).last"
def alltext(path):
    z=zipfile.ZipFile(path); return ' '.join(z.read(n).decode('utf8','ignore') for n in z.namelist() if n.endswith('.xml') or n.endswith('.rels'))
with sync_playwright() as p:
    b=p.chromium.launch(); cx=b.new_context(viewport={'width':1180,'height':820}, accept_downloads=True)
    pg=cx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto(U); pg.wait_for_timeout(300); now=pg.evaluate("Date.now()"); pg.evaluate(SEED, [data, now]); pg.reload(); pg.wait_for_timeout(300)
    # ---- backup reminder ----
    n=pg.locator('#bkNudge'); check(n.count()==1 and 'No backup has been saved' in n.inner_text() and '20 days' in n.inner_text(), 'reminder when nothing was ever backed up and the oldest record is 20 days old')
    pg.screenshot(path=os.path.join(out,'more-backup-nudge.png'))
    check(pg.evaluate("(()=>{return Array.from(document.querySelectorAll('#bkNudge button')).every(e=>e.getBoundingClientRect().height>=43.5)})()"), 'reminder buttons are 44px')
    pg.click('#bkLater'); pg.wait_for_timeout(100); check(pg.locator('#bkNudge').count()==0, 'Not now hides the reminder')
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('#bkNudge').count()==0, 'it stays hidden after Not now')
    pg.evaluate("(now)=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.last.backupSnooze=now-8*864e5; s.last.backupAt=now-15*864e5; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}", now)
    pg.reload(); pg.wait_for_timeout(300); t=pg.locator('#bkNudge').inner_text() if pg.locator('#bkNudge').count() else ''
    check('15 days old' in t and '2 records have changed' in t, 'reminder returns after the snooze, with the age of the last backup: '+t)
    pg.evaluate("(now)=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.last.backupAt=now-13*864e5; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}", now)
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('#bkNudge').count()==0, 'no reminder when the backup is under 14 days old')
    pg.evaluate("(now)=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.last.backupAt=now-30*864e5; Object.values(s.cases).forEach(c=>c.updated=now-40*864e5); localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}", now)
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('#bkNudge').count()==0, 'no reminder when nothing changed since the backup')
    pg.evaluate("(now)=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.cases.c2.updated=now; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}", now)
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('#bkNudge').count()==1, 'reminder is back after an edit')
    pg.click('#bkNow'); pg.wait_for_timeout(200); check(pg.locator('.sheet').count()==1, 'Save a backup file opens the backup sheet')
    pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    # ---- Word export without the name ----
    pg.click('[data-open="c1"]'); pg.wait_for_timeout(150)
    def export(mode, lay):
        pg.click('#export'); pg.wait_for_timeout(150)
        if mode!='full': pg.click(f'[data-wm="{mode}"]')
        if mode=='initials': pg.screenshot(path=os.path.join(out,'more-word-initials.png'))
        check(pg.locator('#wmwarn').is_hidden()==(mode=='full'), mode+': warning shown only when the name is replaced')
        pg.click(f'[data-lay="{lay}"]'); pg.wait_for_selector('#wshare')
        with pg.expect_download() as dl: pg.click('#wshare')
        f=os.path.join(out,f'more_{mode}_{lay}.docx'); dl.value.save_as(f); name=dl.value.suggested_filename
        pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())"); return f, name
    for mode,lab in (('initials','J.R.D.C.'),('alias','Patient A')):
        for lay in ('protocol','form'):
            f,name=export(mode,lay); t=alltext(f)
            for bad in ('Dela Cruz','Juana','004512'):
                check(bad not in t and bad.replace(' ','_') not in name, f'{mode} {lay}: "{bad}" is still in the file or its name ({name})')
            check(lab in t, f'{mode} {lay}: label {lab} missing')
            check(pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases.c1.exported")==None, f'{mode} {lay}: a copy without the name must not count as exported')
    check(pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases.c1.data.patient")=='Dela Cruz, Juana R.', 'the saved record keeps the full name')
    f,name=export('full','protocol'); t=alltext(f)
    check('Dela Cruz' in t and '004512' in t and name.startswith('Dela_Cruz'), 'full name export is unchanged')
    check(pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases.c1.exported")!=None, 'full name export counts as exported')
    # a file without the name reopens as its own record, named by the initials
    pg.click('#back'); pg.wait_for_timeout(200)
    with pg.expect_file_chooser() as fc: pg.click('#imp')
    fc.value.set_files(os.path.join(out,'more_initials_protocol.docx')); pg.wait_for_timeout(1200)
    pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    names=pg.evaluate("Object.values(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).map(c=>c.data.patient)")
    check('J.R.D.C.' in names and 'Dela Cruz, Juana R.' in names, 'the initials file opens as a separate record: '+str(names))
    # ---- rating scales (v42) ----
    pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    pg.goto(U); pg.reload(); pg.wait_for_timeout(300)
    ROS=pg.evaluate("SCHEMAS.case.sections.findIndex(s=>s.id==='ros')")
    pg.click('[data-open="c2"]'); pg.wait_for_timeout(150); pg.click(f'#railList [data-sec="{ROS}"]'); pg.wait_for_timeout(150)
    check(pg.locator('#sc-phq9').inner_text().strip()=='Not scored.' and pg.locator('#sc-gad7').count()==1, 'both scales are in the psychiatric review of systems, not scored')
    pg.click('[data-chk="rosChecks"] >> nth=0'); pg.fill('[data-f="rosDetails"]','Two weeks of low mood.'); pg.wait_for_timeout(150)
    check(pg.evaluate(f"document.querySelector('#railList [data-sec=\"{ROS}\"] .dot').classList.contains('full')"), 'an unscored scale does not keep the section from being complete')
    pg.click('#blanks'); check('PHQ-9' not in pg.locator('.sheet').inner_text(), 'unscored scales are not listed as blank'); pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    pg.click('#back'); pg.wait_for_timeout(200)
    pg.click('[data-open="c1"]'); pg.wait_for_timeout(150); pg.click(f'#railList [data-sec="{ROS}"]'); pg.wait_for_timeout(150)
    rows=pg.locator('[data-rads="phq9"][data-o="2"]'); check(rows.count()==9, 'PHQ-9 has nine items')
    for i in range(8): rows.nth(i).click()
    t=pg.locator('#sc-phq9').inner_text(); check('8 of 9 items scored' in t and 'subtotal 16' in t, 'partly scored PHQ-9 gives no total: '+t)
    pg.locator('[data-rads="phq9"][data-o="1"]').nth(8).click(); pg.wait_for_timeout(100)
    t=pg.locator('#sc-phq9').inner_text(); check('PHQ-9 total 17 of 27' in t and 'moderately severe' in t and 'Item 9 is above 0' in t, 'PHQ-9 total, band and item 9 notice: '+t)
    for i in range(3): pg.locator('[data-rads="gad7"][data-o="3"]').nth(i).click()
    check(pg.locator('[data-rads="gad7"][data-o="0"]').count()==7 and '3 of 7 items scored' in pg.locator('#sc-gad7').inner_text(), 'GAD-7 has seven items, partly scored')
    pg.locator('#sc-phq9').scroll_into_view_if_needed(); pg.screenshot(path=os.path.join(out,'more-scales.png'))
    # bands at their edges
    edges=pg.evaluate("""(()=>{ const mk=(f,t)=>{ const o={}; let left=t; f.p.forEach(([k])=>{ const x=Math.min(3,left); o[k]=String(x); left-=x; }); return scaleScore(f,{[f.id]:o}).band; };
      return [[0,4,5,9,10,14,15,19,20,27].map(t=>mk(SCALE_PHQ9,t)), [0,4,5,9,10,14,15,21].map(t=>mk(SCALE_GAD7,t))]; })()""")
    check(edges[0]==['minimal','minimal','mild','mild','moderate','moderate','moderately severe','moderately severe','severe','severe'], 'PHQ-9 bands: '+str(edges[0]))
    check(edges[1]==['minimal','minimal','mild','mild','moderate','moderate','severe','severe'], 'GAD-7 bands: '+str(edges[1]))
    for lay in ('protocol','form'):
        f,name=export('full',lay); t=re.sub(r'<[^>]+>','',alltext(f))
        check('PHQ-9: 17/27 (moderately severe); item 9 above 0' in t and 'GAD-7: incomplete, 3 of 7 items scored (subtotal 9)' in t, f'scales in the {lay} Word file')
    # the form-layout table reads back into the same scores
    back=pg.evaluate("""async ()=>{ const d=JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases.c1.data; const bytes=DocxGen.build(d,'case',{layout:'form'});
      const z=DocxGen.zip ? null : null; const f=new File([bytes],'x.docx'); const r=await DocxImport.fileToData(f); return [r.data.phq9, r.data.gad7, d.phq9, d.gad7]; }""")
    check(back[0]==back[2] and back[1]==back[3], 'scores survive export and reopen: '+str(back[:2]))
    # slides
    pg.click('#pres'); pg.wait_for_selector('#pgo'); pg.click('#pgo'); pg.wait_for_selector('#pshare', timeout=60000)
    with pg.expect_download() as dl: pg.click('#pshare')
    f=os.path.join(out,'more_scales.pptx'); dl.value.save_as(f); t=re.sub(r'<[^>]+>','',alltext(f))
    check('17/27' in t and 'PHQ-9, moderately severe' in t and 'Item 9 above 0' in t and 'GAD-7 items scored' in t, 'scales on the slides')
    pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    # progress note: last scores shown, new score, Word
    pg.click('#title'); pg.click('#dsPn'); pg.wait_for_timeout(300)
    O=pg.evaluate("SCHEMAS.pn.sections.findIndex(s=>s.id==='pnO')"); pg.click(f'#railList [data-sec="{O}"]'); pg.wait_for_timeout(150)
    t=pg.locator('#main').inner_text(); check('Last documented: 17/27 (moderately severe); item 9 above 0' in t, 'progress note shows the last PHQ-9')
    check(pg.locator('#sc-phq9').inner_text().strip()=='Not scored.', 'scores are not carried into the new note')
    for i in range(7): pg.locator('[data-rads="gad7"][data-o="1"]').nth(i).click()
    check('GAD-7 total 7 of 21' in pg.locator('#sc-gad7').inner_text() and 'mild' in pg.locator('#sc-gad7').inner_text(), 'GAD-7 total in the note')
    pg.click('#export'); pg.wait_for_selector('#wshare, .toast', timeout=20000)
    if pg.locator('#wshare').count():
        with pg.expect_download() as dl: pg.click('#wshare')
        f=os.path.join(out,'more_pn.docx'); dl.value.save_as(f); check('GAD-7: 7/21 (mild)' in re.sub(r'<[^>]+>','',alltext(f)), 'scale in the progress note Word file')
    else: errs.append('progress note export did not offer a file')
    pg.evaluate("document.querySelectorAll('.scrim').forEach(x=>x.remove())")
    pg.once('dialog', lambda d: d.accept()); pg.click('[data-clearscale="gad7"]'); pg.wait_for_timeout(200)
    check(pg.locator('#sc-gad7').inner_text().strip()=='Not scored.' and pg.locator('[data-rads="gad7"][aria-pressed="true"]').count()==0, 'Clear scores')
    pg.click('#back'); pg.wait_for_timeout(200); pg.close()
    q=cx.new_page(); q.set_viewport_size({'width':390,'height':844}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(U+'#/r/c1/ros'); q.reload(); q.wait_for_timeout(300); q.locator('#sc-phq9').scroll_into_view_if_needed()
    check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), 'phone: the scales do not scroll sideways')
    check(q.evaluate("Array.from(document.querySelectorAll('[data-rads=\"phq9\"]')).every(e=>{const r=e.getBoundingClientRect(); return r.width>=43.5&&r.height>=43.5})"), 'phone: score buttons are 44px')
    q.screenshot(path=os.path.join(out,'more-scales-phone.png')); q.close()
    b.close()
print('errors', errs)
