import sys, json; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8819)
data=json.load(open(fx)); errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':820,'height':1180}, has_touch=True); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8819/index.html')
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", data)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]')
    secs = pg.evaluate("Array.from(document.querySelectorAll('#rail [data-sec]')).map(b=>b.textContent.replace(/\\s+/g,' ').trim())")
    for pre, name in [('21','labs'),('25','grid'),('13','fam')]:
        i=[k for k,t in enumerate(secs) if t.startswith(pre) and not t[len(pre)].isdigit()][0]
        pg.evaluate(f"document.querySelector('#rail [data-sec=\"{i}\"]').click()"); pg.wait_for_timeout(250)
        pg.screenshot(path=f'{out}/por_{name}.png')
    print('horizontal overflow:', pg.evaluate("document.documentElement.scrollWidth > innerWidth"))
    b.close()
print('errors', errs)
