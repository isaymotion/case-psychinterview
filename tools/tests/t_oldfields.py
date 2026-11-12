import sys, json, os; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
scripts, work, live, fx = sys.argv[1:5]; start(work, 8815); start(live, 8816)
old = {"patient":"Santos, Pedro","agesex":"52 / M","datetime":"Oct 1, 2026, 10:00 AM","differential":"Bipolar II disorder\nAdjustment disorder","bio":"Family history of depression","psych":"Perfectionism","social":"Job loss",
 "integrated":"Old integrated formulation","primaryDx":"MDD","otherDx":"Hypertension","labs":{"CBC":"normal","TSH":"1.2"},"childhood":"Raised by grandparents","eduwork":"College graduate","relationships":"Married",
 "living":"Lives with wife","legal":"None","vitals":{"BP":"130/80"},"neuro":"Intact","informant":"Patient","reliability":"Good","appChecks":["Cooperative"],"speechChecks":["Slow"],"cycle":"N/A"}
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(accept_downloads=True); pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8816/index.html'); pg.evaluate("localStorage.clear()")
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", old)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]')
    with pg.expect_download() as dl: pg.click('#export')
    f=os.path.join(fx,'old_fields.docx'); dl.value.save_as(f)
    # an old case still stored on the iPad, opened in the new app
    pg.goto('http://127.0.0.1:8815/index.html'); pg.evaluate("localStorage.clear()")
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", old)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]'); pg.wait_for_timeout(200)
    secs = pg.evaluate("Array.from(document.querySelectorAll('#rail [data-sec]')).map(b=>b.innerText.replace(/\\s+/g,' ').trim())")
    i=[k for k,t in enumerate(secs) if t.startswith('23 ')][0]; pg.click(f'#rail [data-sec="{i}"]'); pg.wait_for_timeout(150)
    print('stored old case, section 23 shows older differential:', pg.locator('[data-f="differential"]').count()==1)
    i=[k for k,t in enumerate(secs) if t.startswith('25 ')][0]; pg.click(f'#rail [data-sec="{i}"]'); pg.wait_for_timeout(150)
    print('section 25 shows older bio/psych/social:', [pg.locator(f'[data-f="{k}"]').count() for k in ('bio','psych','social')])
    pg.screenshot(path=os.path.join(fx,'legacy25.png'))
    # the old Word file, opened in the new app
    pg.click('#back'); pg.click('#imp'); pg.set_input_files('#impFile', f); pg.wait_for_selector('[data-close]')
    st=pg.evaluate("JSON.parse(localStorage.getItem('psyCaseApp.v1'))"); rec=sorted(st['cases'].values(), key=lambda c:-c['created'])[0]
    d=rec['data']; bad=[k for k,v in old.items() if d.get(k)!=v]
    print('old Word file -> fields not restored:', bad or 'none', '| unplaced:', pg.locator('.sheet li').all_inner_texts()[:5])
    b.close()
print('errors', errs)
