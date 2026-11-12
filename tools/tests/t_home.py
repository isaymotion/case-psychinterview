# Home screen (v30): layout at four sizes, What's new + unseen badge, search, type chips, delete one record + undo.
# Usage: python3 t_home.py <tests folder> <app folder> <fixture json> <out folder>
import sys, json, os; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8826)
data=json.load(open(fx)); errs=[]
def check(ok, msg):
    if not ok: errs.append(msg)
SEED = """(c)=>{ const now=new Date(2026,9,7);
  const pn = progressFromSource(c,'case',now,'').data;
  const recs = { pn, dc: dischargeFromSources(c,[pn],now,'').data, mc: certFromSource(c,'case',now,{}), ca: abstractFromSources(null,c,pn,now,{}),
    ho: { hoDate:'Oct 7, 2026', unit:'Ward 3B', rows:[handoverRow(c,'case','c1',now)] }, sp: safetyFromSources([{kind:'case',data:c}], now, {}).data };
  const cases={ c1:{id:'c1',kind:'case',created:1,updated:9,data:c} }; let i=2;
  for(const [k,d] of Object.entries(recs)) cases['r'+i]={id:'r'+i,kind:k,created:i,updated:i++,data:d};
  cases.c2={id:'c2',kind:'case',created:20,updated:20,data:{patient:'Zeta Testcase',mrn:'99-0042'}};
  localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases,last:{}})); }"""
N = "Object.keys(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).length"
with sync_playwright() as p:
    b=p.chromium.launch(); cx=b.new_context()   # one context, so every page sees the same saved records
    def page(w,hh,scheme='light'):
        pg=cx.new_page(); pg.set_viewport_size({'width':w,'height':hh}); pg.emulate_media(color_scheme=scheme)
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
        pg.goto('http://127.0.0.1:8826/index.html'); pg.wait_for_timeout(300); return pg
    pg=page(1180,820)
    check(pg.locator('.empty').count()==1 and pg.locator('#wipe').count()==0, 'empty state')
    pg.screenshot(path=os.path.join(out,'home-empty.png'))
    pg.evaluate(SEED, data); pg.reload(); pg.wait_for_timeout(300)
    check(pg.locator('[data-open]').count()==8, 'eight records listed')
    check(pg.locator('#news .badge').inner_text()=='1', 'first visit: one unread entry')
    # no tile, card or bar button may be clipped or overflow the page
    for name,(w,hh,sc) in {'landscape':(1180,820,'light'),'portrait':(820,1180,'light'),'phone':(390,844,'light'),'dark':(1180,820,'dark'),'portrait-dark':(820,1180,'dark')}.items():
        q=page(w,hh,sc)
        check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), name+': page scrolls sideways')
        small=q.evaluate("Array.from(document.querySelectorAll('.starts button,.cases button,.bar button,.fchip')).filter(e=>{const r=e.getBoundingClientRect(); return r.height<43.5||r.width<43.5}).map(e=>e.id||e.className)")
        check(not small, name+': tap targets under 44px '+str(small))
        q.screenshot(path=os.path.join(out,f'home-{name}.png'), full_page=(name!='landscape')); q.close()
    # by patient: one card for the six Dela Cruz documents; the handover and the other patient stand alone
    check(pg.locator('li.pt').count()==1 and pg.locator('li.pt .doc').count()==6 and pg.locator('.cases > li:not(.pt)').count()==2, 'grouped by patient')
    check('MRN 004512' in pg.locator('.pt-head').inner_text() and 'progress note' in pg.locator('.pt-head .who').inner_text().lower(), 'patient card heading')
    pg.click('[data-view="docs"]'); check(pg.locator('li.pt').count()==0 and pg.locator('.cases > li').count()==8, 'All documents view')
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('li.pt').count()==0, 'view remembered')
    pg.select_option('#sort','name'); first=pg.locator('.cases > li strong').first.inner_text(); check(first.startswith('Dela Cruz'), 'sort by name: '+first)
    pg.select_option('#sort','created'); first=pg.locator('.cases > li strong').first.inner_text(); check(first.startswith('Zeta'), 'sort by date created: '+first)
    pg.select_option('#sort','edited'); pg.click('[data-view="pt"]'); check(pg.locator('li.pt').count()==1, 'back to By patient')
    # + Progress note on the patient card starts a note from the newest case or note, then delete it again
    pg.click('[data-newpn]'); pg.wait_for_selector('#back'); check('Dela Cruz' in pg.locator('#title').inner_text(), 'note started from the patient card'); pg.click('#back')
    check(pg.evaluate(N)==9, 'new note saved'); new=pg.evaluate("Object.values(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).sort((a,b)=>b.created-a.created)[0].id")
    pg.click(f'[data-del="{new}"]'); pg.click('[data-yes]'); pg.wait_for_selector('.toast button'); pg.evaluate("document.querySelector('.toast').remove()"); check(pg.evaluate(N)==8, 'extra note removed')
    # exported marks and the clean-up flag
    SET="([id,days,edited])=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.cases[id].exported=Date.now()-days*864e5; s.cases[id].updated=edited?Date.now():1; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}"
    pg.evaluate(SET,['c2',9,False]); pg.evaluate(SET,['r2',0,False]); pg.evaluate(SET,['r3',9,True]); pg.reload(); pg.wait_for_timeout(300)
    check('Exported 9 days ago' in pg.locator('[data-open="c2"]').inner_text() and pg.locator('[data-open="c2"] .tag.warn').count()==1, 'stale record flagged')
    check('Exported today' in pg.locator('[data-open="r2"]').inner_text(), 'exported today')
    check('Edited since export' in pg.locator('[data-open="r3"]').inner_text(), 'edited since export')
    check(pg.locator('.tidy').count()==1 and pg.locator('.fchip[data-k="old"] b').inner_text()=='1', 'clean-up reminder counts one')
    pg.screenshot(path=os.path.join(out,'home-patients.png'))
    pg.click('#tidy'); check(pg.locator('.cases [data-s]:not([hidden])').count()==1 and pg.locator('li.pt').is_hidden(), 'Ready to delete chip shows only that record'); pg.click('.fchip[data-k="all"]')
    # exporting from inside a record marks it
    pg.click('[data-open="r4"]'); pg.wait_for_selector('#export')
    with pg.expect_download():
        pg.click('#export'); pg.wait_for_timeout(200)
        if pg.locator('#wshare').count(): pg.click('#wshare')
    pg.wait_for_timeout(300)
    if pg.locator('.sheet [data-close]').count(): pg.locator('.sheet [data-close]').first.click()
    pg.click('#back')
    check('Exported today' in pg.locator('[data-open="r4"]').inner_text(), 'export marks the record: '+pg.locator('[data-open="r4"]').inner_text()[:80])
    # duplicate MRN notice
    pg.click('#new'); pg.wait_for_selector('[data-f="mrn"]'); pg.fill('[data-f="mrn"]','99 0042'); pg.locator('[data-f="mrn"]').blur(); pg.wait_for_selector('.sheet [data-go]')
    check('Zeta Testcase' in pg.locator('.sheet').inner_text(), 'duplicate MRN notice names the other case'); pg.screenshot(path=os.path.join(out,'dup-mrn.png'))
    pg.click('.sheet [data-close]'); pg.click('#back'); check(pg.locator('.pt-note').count()==1 and pg.locator('li.pt').count()==2, 'two cases under one patient are flagged')
    dup=pg.evaluate("Object.values(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).sort((a,b)=>b.created-a.created)[0].id")
    pg.click(f'[data-del="{dup}"]'); pg.click('[data-yes]'); pg.wait_for_selector('.toast button'); pg.evaluate("document.querySelector('.toast').remove()"); check(pg.evaluate(N)==8, 'duplicate removed')
    # search and chips
    pg.fill('#q','99-0042'); check(pg.locator('.cases [data-s]:not([hidden])').count()==1, 'search by MRN')
    pg.fill('#q','zzz'); check(pg.locator('#nomatch').is_visible(), 'no-match message')
    pg.fill('#q',''); pg.click('.fchip[data-k="case"]'); check(pg.locator('.cases [data-s]:not([hidden])').count()==2, 'Cases chip')
    pg.click('.fchip[data-k="all"]'); check(pg.locator('.cases [data-s]:not([hidden])').count()==8, 'All chip')
    # delete one: cancel, delete, undo, delete for good
    pg.click('[data-del="c2"]'); pg.wait_for_selector('.sheet'); pg.screenshot(path=os.path.join(out,'home-delete.png'))
    pg.click('[data-no]'); check(pg.evaluate(N)==8, 'cancel keeps the record')
    pg.click('[data-del="c2"]'); pg.click('[data-yes]'); pg.wait_for_selector('.toast button')
    check(pg.evaluate(N)==7 and pg.locator('[data-open="c2"]').count()==0, 'record deleted'); pg.screenshot(path=os.path.join(out,'home-undo.png'))
    pg.click('.toast button'); check(pg.evaluate(N)==8 and pg.locator('[data-open="c2"]').count()==1, 'undo brings it back')
    pg.click('[data-del="c2"]'); pg.click('[data-yes]'); pg.reload(); pg.wait_for_timeout(300)
    check(pg.evaluate(N)==7 and pg.locator('[data-open="c1"]').count()==1, 'only that record is gone after reload')
    # delete from inside a record also offers undo
    pg.once('dialog', lambda d: d.accept()); pg.click('[data-open="r7"]'); pg.click('#del'); pg.wait_for_selector('.toast button')
    check(pg.evaluate(N)==6, 'editor delete'); pg.click('.toast button'); check(pg.evaluate(N)==7, 'editor delete undone')
    # delete all, undo, then delete all for good on a throwaway page at the end
    pg.once('dialog', lambda d: d.accept()); pg.click('#back') if pg.locator('#back').count() else None; pg.click('#wipe'); pg.wait_for_selector('.toast button')
    check(pg.evaluate(N)==0 and pg.locator('.empty').count()==1, 'delete all empties the list'); pg.screenshot(path=os.path.join(out,'home-undo-all.png'))
    pg.click('.toast button'); check(pg.evaluate(N)==7 and pg.locator('[data-open]').count()==7, 'undo brings all records back')
    pg.once('dialog', lambda d: d.dismiss()); pg.click('#wipe'); check(pg.evaluate(N)==7, 'cancelling delete all keeps everything')
    # theme button: match device -> light -> dark -> match device; forced dark on a light device really is dark
    BG="getComputedStyle(document.body).backgroundColor"; TH="document.documentElement.getAttribute('data-theme')"
    light=pg.evaluate(BG); pg.click('#theme'); check(pg.evaluate(TH)=='light' and pg.evaluate(BG)==light, 'theme: light')
    pg.click('#theme'); check(pg.evaluate(TH)=='dark' and pg.evaluate(BG)=='rgb(14, 21, 29)', 'theme: forced dark '+pg.evaluate(BG))
    check(pg.evaluate("getComputedStyle(document.querySelector('.fchip[aria-pressed=true]')).color")=='rgb(14, 21, 29)', 'forced dark copies component rules')
    pg.wait_for_timeout(200); pg.screenshot(path=os.path.join(out,'home-forced-dark.png'))
    pg.reload(); pg.wait_for_timeout(300); check(pg.evaluate(TH)=='dark', 'theme remembered'); pg.click('#theme'); check(pg.evaluate(TH) is None, 'theme: back to match device')
    q=page(1180,820,'dark'); q.click('#theme'); check(q.evaluate(BG)==light, 'forced light on a dark device'); q.click('#theme'); q.click('#theme'); q.close()
    # text size: every size, no sideways scroll on home or inside a case at three widths; remembered
    pg.click('#aa'); pg.wait_for_selector('[data-size]'); pg.click('[data-size="3"]'); pg.screenshot(path=os.path.join(out,'look-sheet.png')); pg.click('[data-close]')
    check(pg.evaluate("getComputedStyle(document.body).zoom")=='1.25', 'Larger text applied')
    for i in range(4):
        pg.evaluate("i=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.last.textSize=i; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}", i)
        for w,hh in [(1180,820),(820,1180),(390,844)]:
            q=page(w,hh); check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), f'size {i} at {w}: home scrolls sideways')
            if i==3: q.screenshot(path=os.path.join(out,f'home-larger-{w}.png'))
            q.click('[data-open="c1"]'); q.wait_for_timeout(150); check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), f'size {i} at {w}: case scrolls sideways')
            if w==1180: check(q.evaluate("(()=>{const r=document.querySelector('#rail').getBoundingClientRect(); return r.bottom<=window.innerHeight+1})()"), f'size {i}: section list taller than the screen')
            if i==3: q.screenshot(path=os.path.join(out,f'case-larger-{w}.png'))
            q.click('#back') if q.locator('#back').is_visible() else None; q.close()
    pg.evaluate("()=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); s.last.textSize=1; localStorage.setItem('psyCaseApp.v1',JSON.stringify(s));}"); pg.reload(); pg.wait_for_timeout(300)
    # backup (plain and with a password), restore into an empty app, wrong password, undo; a hostile file adds nothing
    import tempfile; tmp=tempfile.mkdtemp()
    def pick(f):
        with pg.expect_file_chooser() as fc: pg.click('#bkOpen')
        fc.value.set_files(f)
    def backup(pw):
        pg.click('#bkSave'); pg.wait_for_selector('#bkGo')
        if pw: pg.fill('#bk1',pw); pg.fill('#bk2',pw)
        pg.click('#bkGo'); pg.wait_for_selector('#bkShare')
        with pg.expect_download() as d: pg.click('#bkShare')
        f=os.path.join(tmp,('enc' if pw else 'plain')+'.json'); d.value.save_as(f); pg.click('.sheet [data-close]'); return f
    pg.click('#bkSave'); pg.wait_for_selector('#bkGo'); pg.fill('#bk1','abcdef'); pg.fill('#bk2','abcdeg'); pg.click('#bkGo')
    check('do not match' in pg.inner_text('#bkErr'), 'mismatched backup passwords are refused'); pg.click('.sheet [data-close]')
    n0=pg.evaluate(N); plain=backup(''); enc=backup('s3cret-pw'); pj=json.load(open(plain)); ej=json.load(open(enc))
    check(pj.get('app')=='psychinterview' and len(pj.get('cases',{}))==n0, 'plain backup holds every record')
    check('cases' not in ej and 'enc' in ej and 'Dela Cruz' not in open(enc).read(), 'password backup is not readable')
    check('Last backup saved' in pg.inner_text('.backup'), 'last backup time shown')
    pg.screenshot(path=os.path.join(out,'home-backup.png'), full_page=True)
    pg.once('dialog', lambda d: d.accept()); pg.click('#wipe'); pg.wait_for_selector('.toast button'); pg.reload(); pg.wait_for_timeout(300)
    check(pg.evaluate(N)==0 and pg.locator('#bkSave').count()==0 and pg.locator('#bkOpen').count()==1, 'empty app still offers Restore')
    pick(enc); pg.wait_for_selector('#bkPw'); pg.fill('#bkPw','wrong'); pg.click('#bkGo'); pg.wait_for_timeout(1500)
    check('did not open' in pg.inner_text('#bkErr'), 'wrong backup password'); pg.fill('#bkPw','s3cret-pw'); pg.click('#bkGo'); pg.wait_for_selector('#bkDo', timeout=15000)
    pg.screenshot(path=os.path.join(out,'home-restore.png')); pg.click('#bkDo'); pg.wait_for_selector('.toast button')
    check(pg.evaluate(N)==n0, 'restore brings every record back'); pg.click('.toast button'); check(pg.evaluate(N)==0, 'restore undone')
    pick(plain); pg.wait_for_selector('#bkDo'); pg.click('#bkDo'); pg.wait_for_timeout(200); check(pg.evaluate(N)==n0, 'plain restore')
    pick(plain); pg.wait_for_selector('.sheet h3'); check(pg.locator('#bkDo').count()==0, 'nothing to restore when all records are already here'); pg.click('.sheet [data-close]')
    bad=os.path.join(tmp,'bad.json'); json.dump({'app':'psychinterview','kind':'backup','format':1,'made':'2026-11-12T00:00:00Z','cases':{'x':{'id':'x"><img src=x onerror=alert(1)>','kind':'case','data':{}},'y':{'id':'y','kind':'nope','data':{}}}}, open(bad,'w'))
    pick(bad); pg.wait_for_timeout(400); check(pg.evaluate(N)==n0 and pg.locator('#bkDo').count()==0, 'hostile backup entries are skipped')
    notbk=os.path.join(tmp,'no.json'); open(notbk,'w').write('{"hello":1}'); pick(notbk); pg.wait_for_timeout(300); check('not a PsychInterview backup' in pg.inner_text('.toast'), 'other json refused')
    # Export all on a patient card: one zip with every Word file, and each record marked exported
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-expall] >> nth=0'); pg.wait_for_selector('#xshare', timeout=60000); pg.screenshot(path=os.path.join(out,'home-export-all.png'))
    nfiles=pg.locator('.sheet li').count()
    with pg.expect_download() as d: pg.click('#xshare')
    zf=os.path.join(tmp,'all.zip'); d.value.save_as(zf)
    import zipfile; names=zipfile.ZipFile(zf).namelist()
    check(d.value.suggested_filename.endswith('.zip') and len(names)==nfiles and nfiles>=2 and len(set(names))==nfiles and all(x.endswith('.docx') for x in names), f'export all zip {names}')
    check(zipfile.ZipFile(zf).testzip() is None, 'zip is sound')
    check(pg.evaluate("Object.values(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).filter(c=>c.exported).length")>=nfiles, 'export all marks the records exported')
    # passcode lock: set, lock now, wrong and right passcode, locked at start-up with no record in the page, idle lock, change, forgot, turn off
    LOCK="!!JSON.parse(localStorage.getItem('psyCaseApp.v1')).last.lock"
    pg.reload(); pg.wait_for_timeout(300); pg.click('#lockSet'); pg.wait_for_selector('#lk1'); pg.fill('#lk1','12a4'); pg.fill('#lk2','12a4'); pg.click('#lkGo')
    check('4 to 8 digits' in pg.inner_text('#lkErr'), 'non-numeric passcode refused'); pg.fill('#lk1','2468'); pg.fill('#lk2','2469'); pg.click('#lkGo'); pg.wait_for_timeout(100)
    check('do not match' in pg.inner_text('#lkErr'), 'mismatched passcodes refused'); pg.fill('#lk2','2468'); pg.click('#lkGo'); pg.wait_for_selector('#lockNow')
    check(pg.evaluate(LOCK) and '2468' not in pg.evaluate("localStorage.getItem('psyCaseApp.v1')"), 'lock saved, passcode itself is not stored')
    pg.screenshot(path=os.path.join(out,'home-lock-card.png'), full_page=True)
    pg.click('#lockNow'); pg.wait_for_selector('#lockPin'); pg.screenshot(path=os.path.join(out,'lock.png'))
    check(pg.evaluate("document.querySelector('main').inert===true"), 'page under the lock is inert')
    pg.fill('#lockPin','1111'); pg.keyboard.press('Enter'); pg.wait_for_timeout(700); check('not right' in pg.inner_text('#lockErr') and pg.locator('.lock').count()==1, 'wrong passcode keeps it locked')
    pg.fill('#lockPin','2468'); pg.keyboard.press('Enter'); pg.wait_for_selector('.lock', state='detached'); check(pg.evaluate("document.querySelector('main').inert===false"), 'unlocked page works again')
    pg.reload(); pg.wait_for_selector('#lockPin'); check(pg.locator('.cases li, .pt, main').count()==0 and 'Dela Cruz' not in pg.content(), 'no patient detail in the page before unlocking at start-up')
    check(pg.title()=='PsychInterview', 'neutral title while locked')
    pg.fill('#lockPin','2468'); pg.keyboard.press('Enter'); pg.wait_for_selector('[data-open]'); check(pg.locator('.lock').count()==0, 'start-up unlock shows the records')
    q=cx.new_page(); q.set_viewport_size({'width':1180,'height':820}); q.clock.install(); q.goto('http://127.0.0.1:8826/index.html'); q.wait_for_selector('#lockPin'); q.fill('#lockPin','2468'); q.keyboard.press('Enter'); q.wait_for_selector('[data-open]')
    q.click('[data-open="c1"]'); q.wait_for_selector('#export'); q.clock.fast_forward('04:30'); check(q.locator('.lock').count()==0, 'not locked before the idle time')
    q.clock.fast_forward('01:00'); q.wait_for_selector('#lockPin'); check(q.title()=='PsychInterview', 'idle lock hides the patient name in the title')
    q.fill('#lockPin','2468'); q.keyboard.press('Enter'); q.wait_for_selector('.lock', state='detached'); check(q.locator('#export').count()==1 and 'Dela Cruz' in q.title(), 'idle unlock returns to the open record'); q.close()
    pg.select_option('#lockIdle','1'); check(pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1')).last.lock.idle")==1, 'idle time saved')
    pg.click('#lockChange'); pg.wait_for_selector('#lk0'); pg.fill('#lk0','0000'); pg.fill('#lk1','13579'); pg.fill('#lk2','13579'); pg.click('#lkGo'); pg.wait_for_timeout(700)
    check('current passcode' in pg.inner_text('#lkErr'), 'change needs the current passcode'); pg.fill('#lk0','2468'); pg.click('#lkGo'); pg.wait_for_selector('.sheet', state='detached')
    n1=pg.evaluate(N); pg.click('#lockNow'); pg.fill('#lockPin','2468'); pg.keyboard.press('Enter'); pg.wait_for_timeout(700); check(pg.locator('.lock').count()==1, 'old passcode no longer works')
    pg.click('#lockForgot'); pg.click('#lockBack'); pg.fill('#lockPin','13579'); pg.keyboard.press('Enter'); pg.wait_for_selector('.lock', state='detached'); check(pg.evaluate(N)==n1, 'forgot then back erases nothing')
    pg.click('#lockOff'); pg.wait_for_selector('#lk0'); pg.fill('#lk0','13579'); pg.click('#lkGo'); pg.wait_for_selector('#lockSet'); check(not pg.evaluate(LOCK), 'lock turned off')
    q=cx.new_page(); q.set_viewport_size({'width':820,'height':1180}); q.goto('http://127.0.0.1:8826/index.html'); q.wait_for_timeout(300)   # forgot -> erase, on a copy of the data put back afterwards
    keep=q.evaluate("localStorage.getItem('psyCaseApp.v1')"); q.click('#lockSet'); q.fill('#lk1','4321'); q.fill('#lk2','4321'); q.click('#lkGo'); q.wait_for_selector('#lockNow'); q.click('#lockNow'); q.click('#lockForgot'); q.screenshot(path=os.path.join(out,'lock-forgot.png'))
    q.once('dialog', lambda d: d.accept()); q.click('#lockErase'); q.wait_for_selector('.empty'); check(q.evaluate(N)==0 and not q.evaluate(LOCK), 'forgot: erase removes records and the lock')
    q.evaluate("v=>localStorage.setItem('psyCaseApp.v1',v)", keep); q.close(); pg.reload(); pg.wait_for_timeout(300); check(pg.evaluate(N)==n1, 'records back for the remaining checks')
    # dark top bar inside a record, with Aa
    pg.click('[data-open="c1"]'); pg.wait_for_selector('#export'); check(pg.evaluate("getComputedStyle(document.querySelector('header.bar')).backgroundColor")=='rgb(27, 45, 69)', 'record top bar is dark')
    pg.click('#aa'); pg.wait_for_selector('[data-size]'); pg.click('[data-size="2"]'); check(pg.evaluate("getComputedStyle(document.body).zoom")=='1.12', 'Aa works inside a record'); pg.click('[data-size="1"]'); pg.click('[data-close]')
    pg.screenshot(path=os.path.join(out,'case-bar.png'))
    for w in (820,390):
        q=cx.new_page(); q.set_viewport_size({'width':w,'height':1000}); q.goto('http://127.0.0.1:8826/index.html'); q.wait_for_timeout(300); q.click('[data-open="c1"]'); q.wait_for_selector('#export')
        clipped=q.evaluate("Array.from(document.querySelectorAll('header.bar button')).filter(e=>{const r=e.getBoundingClientRect(); return r.width>0 && (r.right>window.innerWidth+1 || r.width<43.5)}).map(e=>e.id)")
        check(not clipped, f'record bar at {w}: {clipped}'); q.screenshot(path=os.path.join(out,f'case-bar-{w}.png'), clip={'x':0,'y':0,'width':w,'height':200}); q.close()
    pg.mouse.click(40,30); pg.wait_for_selector('#news')
    # What's new
    pg.click('#news'); pg.wait_for_selector('.news-entry')
    check(pg.locator('.news-entry.is-new').count()==1, 'one entry marked new'); pg.screenshot(path=os.path.join(out,'news.png'))
    vers=pg.evaluate("Array.from(document.querySelectorAll('.news-date small')).map(e=>e.textContent)")
    sw=open(os.path.join(root,'sw.js')).read().split("PREFIX + '")[1].split("'")[0]
    check(vers and vers[0]=='Version '+sw.lstrip('v'), f"newest What's new entry {vers[:1]} does not match sw.js cache {sw}")
    pg.click('#back'); check(pg.locator('#news .badge').count()==0 and pg.locator('#newsStrip').count()==0, 'badge cleared after reading')
    pg.reload(); pg.wait_for_timeout(300); check(pg.locator('#news .badge').count()==0, 'badge stays cleared')
    q=page(390,844); q.click('#news'); q.wait_for_selector('.news-entry'); q.screenshot(path=os.path.join(out,'news-phone.png')); q.close()
    b.close()
print('errors', errs)
