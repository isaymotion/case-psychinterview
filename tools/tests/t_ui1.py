import sys, json; sys.path.insert(0, sys.argv[1])
from serve import start
from playwright.sync_api import sync_playwright
root=sys.argv[2]; out=sys.argv[3]; start(root, 8811)
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1180,'height':820}, has_touch=True)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8811/index.html'); pg.wait_for_timeout(300)
    pg.click('#new'); pg.wait_for_timeout(200)
    pg.fill('[data-f="patient"]','Dela Cruz, Juana R.'); pg.fill('[data-f="agesex"]','34 / F')
    # section indexes by title
    secs = pg.evaluate("Array.from(document.querySelectorAll('#rail [data-sec]')).map(b=>b.innerText.replace(/\\s+/g,' ').trim())")
    print(len(secs), secs[:6], secs[-4:])
    def go(prefix):
        i=[k for k,t in enumerate(secs) if t.startswith(prefix+' ')][0]; pg.click(f'#rail [data-sec="{i}"]'); pg.wait_for_timeout(120)
    go('B'); pg.fill('[data-f="caseTitle"]','A case of major depressive disorder'); pg.fill('[data-f="objectives"][data-li="0"]','To discuss a case of MDD')
    go('13')
    for i,(n,r,a) in enumerate([('Ramon','Father','62'),('Lourdes','Mother','58'),('Ana','Sister','30')]):
        pg.click('[data-famadd]'); pg.fill(f'[data-fam="{i}"][data-fk="name"]', n); pg.select_option(f'[data-fam="{i}"][data-fk="rel"]', r); pg.fill(f'[data-fam="{i}"][data-fk="age"]', a)
    pg.click('[data-famtog="2"][data-fk="psych"]'); pg.fill('[data-fam="2"][data-fk="cond"]','MDD')
    pg.click('[data-rad="parentsRel"][data-o="Separated"]')
    pg.wait_for_timeout(400); pg.screenshot(path=out+'/ui-fam.png', full_page=True)
    go('21'); pg.fill('[data-lab="cbc"][data-lr="0"][data-lc="1"]','11.5'); pg.fill('[data-lab="cbc"][data-lr="2"][data-lc="1"]','6,670'); pg.fill('[data-labtext="ua"]','Yellow, slightly hazy')
    print('flag hb:', pg.inner_text('#lf-cbc-0'), '| flag wbc:', repr(pg.inner_text('#lf-cbc-2')))
    pg.screenshot(path=out+'/ui-labs.png')
    go('25'); pg.fill('[data-grid="bps"][data-gk="Predisposing|Biological"]','Family history of depression')
    pg.screenshot(path=out+'/ui-grid.png')
    go('29'); pg.wait_for_timeout(100)
    pg.wait_for_timeout(600)
    d=pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('psyCaseApp.v1')); return Object.values(s.cases)[0].data})()")
    print('saved:', json.dumps({k:d.get(k) for k in ['caseTitle','objectives','parentsRel','bps','refs']})[:500])
    print('family:', d.get('family')); print('labs:', json.dumps(d.get('labPanels'))[:200])
    b.close()
print('errors', errs)
