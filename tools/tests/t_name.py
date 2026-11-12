import sys; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
start(sys.argv[2], 8821); errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1180,'height':820}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8821/index.html'); pg.wait_for_timeout(400)
    print('tab title:', pg.title(), '| heading:', pg.inner_text('header h1')); pg.screenshot(path='name.png')
    b.close()
print('errors', errs)
