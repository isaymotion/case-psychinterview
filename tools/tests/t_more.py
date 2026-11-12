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
    b.close()
print('errors', errs)
