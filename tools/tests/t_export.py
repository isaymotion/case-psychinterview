import sys, json, os; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root, fx, out = sys.argv[2], sys.argv[3], sys.argv[4]; start(root, 8812)
data = json.load(open(fx))
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1180,'height':820}, accept_downloads=True)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8812/index.html'); pg.wait_for_timeout(300)
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}}, last:{}})); }", data)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]'); pg.wait_for_timeout(200)
    for lay in ['protocol','form']:
        pg.click('#export'); pg.wait_for_selector(f'[data-lay="{lay}"]')
        if lay=='protocol': pg.screenshot(path=out+'/exp-sheet.png')
        pg.click(f'[data-lay="{lay}"]'); pg.wait_for_selector('#wshare', timeout=15000)
        with pg.expect_download() as dl: pg.click('#wshare')
        dl.value.save_as(os.path.join(out, f'case_{lay}.docx')); print(lay, dl.value.suggested_filename)
        pg.click('[data-close]')
    b.close()
print('errors', errs)
