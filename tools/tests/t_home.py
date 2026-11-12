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
    check(pg.locator('.cases li').count()==8, 'eight records listed')
    check(pg.locator('#news .badge').inner_text()=='1', 'first visit: one unread entry')
    # no tile, card or bar button may be clipped or overflow the page
    for name,(w,hh,sc) in {'landscape':(1180,820,'light'),'portrait':(820,1180,'light'),'phone':(390,844,'light'),'dark':(1180,820,'dark'),'portrait-dark':(820,1180,'dark')}.items():
        q=page(w,hh,sc)
        check(q.evaluate("document.documentElement.scrollWidth<=window.innerWidth"), name+': page scrolls sideways')
        small=q.evaluate("Array.from(document.querySelectorAll('.starts button,.cases button,.bar button,.fchip')).filter(e=>{const r=e.getBoundingClientRect(); return r.height<43.5||r.width<43.5}).map(e=>e.id||e.className)")
        check(not small, name+': tap targets under 44px '+str(small))
        q.screenshot(path=os.path.join(out,f'home-{name}.png'), full_page=(name!='landscape')); q.close()
    # search and chips
    pg.fill('#q','99-0042'); check(pg.locator('.cases li:not([hidden])').count()==1, 'search by MRN')
    pg.fill('#q','zzz'); check(pg.locator('#nomatch').is_visible(), 'no-match message')
    pg.fill('#q',''); pg.click('.fchip[data-k="case"]'); check(pg.locator('.cases li:not([hidden])').count()==2, 'Cases chip')
    pg.click('.fchip[data-k="all"]'); check(pg.locator('.cases li:not([hidden])').count()==8, 'All chip')
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
    pg.click('.toast button'); check(pg.evaluate(N)==7 and pg.locator('.cases li').count()==7, 'undo brings all records back')
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
