# Navigation (v38): resume + Continue card, address and back, find in a record, three-state dots, What's still blank, patient's documents.
# Usage: python3 t_nav.py <tests folder> <app folder> <fixture json> <out folder>
import sys, json, os; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8827)
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
U='http://127.0.0.1:8827/index.html'
cur_sec = "document.querySelector('#railList button.cur').dataset.sec"
with sync_playwright() as p:
    b=p.chromium.launch(); cx=b.new_context(viewport={'width':1180,'height':820})
    pg=cx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto(U); pg.wait_for_timeout(300); pg.evaluate(SEED, data); pg.reload(); pg.wait_for_timeout(300)
    check(pg.locator('#cont').count()==0, 'no Continue card before any record was opened')
    # resume + address
    pg.click('[data-open="c1"]'); pg.wait_for_timeout(150)
    check(pg.evaluate(cur_sec)=='0' and '#/r/c1/' in pg.url, 'a record opens at its first section, address names it: '+pg.url)
    pg.click('#railList [data-sec="8"]'); pg.wait_for_timeout(150); sec8=pg.locator('.sec-head h2').inner_text()
    check(pg.url.endswith('#/r/c1/'+pg.evaluate("SCHEMAS.case.sections[8].id")), 'address follows the section')
    check('Dela Cruz' not in pg.url and '004512' not in pg.url, 'no patient detail in the address')
    pg.click('#back'); pg.wait_for_timeout(200)
    check(pg.locator('main.home').count()==1 and '#' not in pg.url, 'Records button returns home with a clean address: '+pg.url)
    c=pg.locator('#cont'); check(c.count()==1 and 'Dela Cruz' in c.inner_text() and sec8.split('. ',1)[1] in c.inner_text(), 'Continue card names the record and section')
    pg.screenshot(path=os.path.join(out,'nav-continue.png'))
    c.click(); pg.wait_for_timeout(150); check(pg.evaluate(cur_sec)=='8', 'Continue reopens at the section last used')
    pg.go_back(); pg.wait_for_timeout(250); check(pg.locator('main.home').count()==1, 'back swipe from a record shows the home screen')
    pg.go_forward(); pg.wait_for_timeout(250); check(pg.locator('#railList').count()==1 and pg.evaluate(cur_sec)=='8', 'forward returns to the record and section')
    pg.reload(); pg.wait_for_timeout(350); check(pg.locator('#railList').count()==1 and pg.evaluate(cur_sec)=='8', 'reload keeps the record and section')
    pg.go_back(); pg.wait_for_timeout(250); check(pg.locator('main.home').count()==1, 'back after a reload shows the home screen')
    pg.click('#news'); pg.wait_for_timeout(150); check(pg.url.endswith('#/news'), "What's new has an address")
    pg.go_back(); pg.wait_for_timeout(250); check(pg.locator('main.home').count()==1, "back from What's new shows the home screen")
    pg.click('#news'); pg.click('#back'); pg.wait_for_timeout(250); check(pg.locator('main.home').count()==1 and '#' not in pg.url, "Records button on What's new")
    pg.goto(U+'#/r/nosuchrecord/x'); pg.reload(); pg.wait_for_timeout(300); check(pg.locator('main.home').count()==1, 'an address for a record that is gone shows the home screen')
    # dots: three states
    pg.click('[data-open="c2"]'); pg.wait_for_timeout(150)
    check(pg.evaluate("(()=>{const d=document.querySelector('#railList [data-sec=\"0\"] .dot'); return d.classList.contains('on') && !d.classList.contains('full') && d.getAttribute('aria-label')==='partly filled'})()"), 'partly filled section has a half dot')
    check(pg.evaluate("document.querySelector('#railList [data-sec=\"3\"] .dot').className.trim()")=='dot', 'empty section has a hollow dot')
    # what is still blank
    pg.click('#blanks'); pg.wait_for_timeout(150)
    t=pg.locator('.sheet').inner_text().lower(); check('not started' in t and 'partly filled' in t and 'blank:' in t, 'blank sheet lists both groups')
    pg.screenshot(path=os.path.join(out,'nav-blanks.png'))
    pg.locator('.sheet [data-bf]').first.click(); pg.wait_for_timeout(200)
    check(pg.evaluate(cur_sec)=='0' and pg.locator('.flash').count()==1, 'tapping a partly filled section goes to its first blank field')
    pg.click('#export'); pg.wait_for_timeout(150); check(pg.locator('#seeBlanks').count()==1, 'export sheet mentions blank sections')
    pg.click('#seeBlanks'); pg.wait_for_timeout(150); check("What's still blank" in pg.locator('.sheet h3').inner_text(), 'See which opens the list')
    pg.locator('.sheet [data-bs]').first.click(); pg.wait_for_timeout(150)
    pg.fill('[data-f]:visible >> nth=0', 'x'); pg.wait_for_timeout(100)
    pg.click('#back'); pg.wait_for_timeout(200)
    # find in a record
    pg.click('[data-open="c1"]'); pg.wait_for_timeout(150)
    check(pg.locator('#railList .dot.full').count()>5, 'the full fixture has complete sections')
    pg.fill('#find','sertraline'); pg.wait_for_timeout(150)
    n=pg.locator('#railList .hit').count(); check(n>=2 and pg.locator('#railList mark').count()>=2, 'find lists typed text with the word marked: %d'%n)
    pg.screenshot(path=os.path.join(out,'nav-find.png'))
    pg.locator('#railList .hit[data-hf]').first.click(); pg.wait_for_timeout(250)
    check(pg.locator('.flash').count()==1 and pg.evaluate("(()=>{const r=document.querySelector('.flash').getBoundingClientRect(); return r.top>=0 && r.top<innerHeight})()"), 'a hit scrolls to its field and marks it')
    check('sertraline' in pg.evaluate("document.querySelector('.flash').innerText + Array.from(document.querySelectorAll('.flash [data-f]')).map(e=>e.value).join(' ')").lower(), 'the marked field holds the word')
    check(pg.input_value('#find')=='sertraline' and pg.locator('#railList .hit').count()==n, 'results stay after a jump')
    pg.fill('#find','mrn'); pg.wait_for_timeout(150); check(pg.locator('#railList .hit').count()>=1, 'find matches a field name')
    pg.fill('#find','mental status'); pg.wait_for_timeout(150); check('Section' in pg.locator('#railList').inner_text(), 'find matches a section name')
    pg.fill('#find','zzqq'); pg.wait_for_timeout(150); check(pg.locator('#railList .nohit').count()==1, 'no match message')
    pg.fill('#find','<b>'); pg.wait_for_timeout(100); check(pg.locator('#railList b').count()==0, 'typed markup is not drawn')
    pg.fill('#find',''); pg.wait_for_timeout(150); check(pg.locator('#railList [data-sec]').count()==pg.evaluate("SCHEMAS.case.sections.length"), 'clearing the box brings the sections back')
    # the patient's documents
    pg.click('#title'); pg.wait_for_timeout(150)
    check(pg.locator('.sheet [data-go]').count()==6 and pg.locator('.sheet [data-go][aria-current]').count()==1 and pg.locator('#dsPn').count()==1, 'documents sheet lists the six documents of this patient')
    pg.screenshot(path=os.path.join(out,'nav-docs.png'))
    pg.locator('.sheet [data-go]:not([aria-current])').first.click(); pg.wait_for_timeout(200)
    check('#/r/c1/' not in pg.url and '#/r/' in pg.url, 'switching opens the other document')
    pg.go_back(); pg.wait_for_timeout(250); check(pg.locator('main.home').count()==1, 'one back from a switched document shows the home screen')
    n0=pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).length")
    pg.click('[data-open="c1"]'); pg.click('#title'); pg.click('#dsPn'); pg.wait_for_timeout(300)
    check(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('psyCaseApp.v1')).cases).length")==n0+1 and 'Progress note' in pg.locator('#title').inner_text(), '+ Progress note from inside a record')
    pg.click('#back'); pg.wait_for_timeout(200)
    pg.click('.cases [data-kind="ho"] [data-open]'); pg.wait_for_timeout(150); check(pg.locator('#title.tap').count()==0 and pg.locator('#find').count()==1, 'handover: no documents sheet, find is there')
    pg.fill('#find','dela'); pg.wait_for_timeout(150); check(pg.locator('#railList .hit').count()>=1, 'find reads the handover patients')
    pg.click('#back'); pg.wait_for_timeout(200)
    pg.close()
    # narrow screens: the drawer holds the find box; nothing scrolls sideways; tap targets
    for w,hh in ((820,1180),(390,844)):
        q=cx.new_page(); q.set_viewport_size({'width':w,'height':hh}); q.on('pageerror', lambda e: errs.append(str(e)))
        q.goto(U); q.wait_for_timeout(300)
        check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), f'{w}: home scrolls sideways')
        check(q.evaluate("(()=>{const r=document.querySelector('#cont').getBoundingClientRect(); return r.height>=44})()"), f'{w}: Continue card height')
        q.screenshot(path=os.path.join(out,f'nav-home-{w}.png'))
        q.goto(U+'#/r/c1'); q.reload(); q.wait_for_timeout(300); q.click('#menu'); q.wait_for_timeout(300)
        small=q.evaluate("Array.from(document.querySelectorAll('.rail-top input,.rail-top button')).filter(e=>{const r=e.getBoundingClientRect(); return r.height<43.5}).map(e=>e.id)")
        check(not small, f'{w}: rail tap targets under 44px {small}')
        q.fill('#find','sertraline'); q.wait_for_timeout(150); q.screenshot(path=os.path.join(out,f'nav-find-{w}.png'))
        q.locator('#railList .hit[data-hf]').first.click(); q.wait_for_timeout(350)
        check(not q.evaluate("document.querySelector('#rail').classList.contains('open')") and q.locator('.flash').count()==1, f'{w}: a hit closes the drawer and shows the field')
        check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), f'{w}: record scrolls sideways')
        q.click('#back'); q.wait_for_timeout(200); check(q.locator('main.home').count()==1, f'{w}: Records after a direct address'); q.close()
    b.close()
print('errors', errs)
