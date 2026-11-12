import sys, json, os, re, io, zipfile; sys.path.insert(0, sys.argv[1])
from serve import start
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
root, fx = sys.argv[2], sys.argv[3]; start(root, 8820)
data=json.load(open(fx)); errs=[]; log=[]; uploads=[]; fail401={'n':0}
CORS={'Access-Control-Allow-Origin':'http://127.0.0.1:8820','Access-Control-Allow-Headers':'authorization,content-type,x-upload-content-type','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS','Access-Control-Expose-Headers':'Location'}
def google_auth(route):
    q=parse_qs(urlparse(route.request.url).query); log.append(('signin', q['scope'][0], q['redirect_uri'][0], q['client_id'][0]))
    route.fulfill(status=302, headers={'Location': q['redirect_uri'][0]+'#access_token=TOKEN'+str(len(log))+'&token_type=Bearer&expires_in=3599&state='+q['state'][0]})
def api(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=200, headers=CORS)
    url=r.url
    if fail401['n']>0 and '/upload/' in url: fail401['n']-=1; return route.fulfill(status=401, headers=CORS, body='{}')
    if url.startswith('https://www.googleapis.com/drive/v3/files?') and r.method=='POST':
        log.append(('folder', json.loads(r.post_data)['name'])); return route.fulfill(status=200, headers=CORS, content_type='application/json', body='{"id":"FOLDER1"}')
    if url.startswith('https://www.googleapis.com/drive/v3/files/FOLDER1'):
        log.append(('folder-check',)); return route.fulfill(status=200, headers=CORS, content_type='application/json', body='{"id":"FOLDER1","trashed":false}')
    if 'uploadType=multipart' in url:
        body=r.post_data_buffer; ctype=r.headers['content-type']; bd=ctype.split('boundary=')[1]
        parts=body.split(('--'+bd).encode())
        meta=json.loads(parts[1].split(b'\r\n\r\n',1)[1].strip()); media=parts[2].split(b'\r\n\r\n',1)[1][:-2]
        uploads.append(('multipart', meta, media, r.headers.get('authorization')))
        return route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'id':'F'+str(len(uploads)),'name':meta['name'],'webViewLink':'https://docs.google.com/x/'+str(len(uploads))}))
    if 'uploadType=resumable' in url:
        uploads.append(('resumable-start', json.loads(r.post_data), b'', r.headers.get('authorization')))
        return route.fulfill(status=200, headers={**CORS,'Location':'https://www.googleapis.com/upload/session/ABC'}, body='')
    if url.startswith('https://www.googleapis.com/upload/session/ABC') and r.method=='PUT':
        meta=uploads[-1][1]; uploads.append(('resumable-put', meta, r.post_data_buffer, None))
        return route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps({'id':'R1','name':meta['name'],'webViewLink':'https://docs.google.com/r/1'}))
    route.fulfill(status=404, headers=CORS, body='{}')
def ok_file(b, kind):
    z=zipfile.ZipFile(io.BytesIO(b)); return ('word/document.xml' if kind=='doc' else 'ppt/presentation.xml') in z.namelist()
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1180,'height':820}, accept_downloads=True)
    ctx.route('https://accounts.google.com/**', google_auth); ctx.route('https://www.googleapis.com/**', api)
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8820/index.html'); pg.wait_for_timeout(300)
    pg.evaluate("d=>{ localStorage.setItem('psyCaseApp.v1', JSON.stringify({cases:{c1:{id:'c1',kind:'case',created:1,updated:2,data:d}, p1:{id:'p1',kind:'pn',created:3,updated:3,data:{patient:'Dela Cruz, Juana R.',mrn:'004512',datetime:'Oct 7, 2026',hday:'8',interval:'Better.'}}}, last:{}})); }", data)
    pg.reload(); pg.wait_for_timeout(300); pg.click('[data-open="c1"]')
    # 1. case protocol to Google Docs (first time: signs in, comes back, finishes)
    pg.click('#export'); pg.click('[data-lay="protocol"]'); pg.wait_for_selector('#wgoogle'); pg.click('#wgoogle')
    pg.wait_for_selector('text=Saved to Google Docs', timeout=20000); pg.screenshot(path='gt-doc.png')
    print('1 case protocol ->', uploads[-1][0], uploads[-1][1], '| valid docx:', ok_file(uploads[-1][2],'doc'), '| url after return:', pg.url)
    pg.click('[data-close]')
    # 2. same session: no second sign-in
    n=len([l for l in log if l[0]=='signin'])
    pg.click('#export'); pg.click('[data-lay="form"]'); pg.wait_for_selector('#wgoogle'); pg.click('#wgoogle'); pg.wait_for_selector('text=Saved to Google Docs', timeout=20000)
    print('2 case form -> new sign-ins:', len([l for l in log if l[0]=='signin'])-n, '| name:', uploads[-1][1]['name'], '| folder reused:', ('folder-check',) in log); pg.click('[data-close]')
    # 3. slides, small design (one-step) and large design (two-step)
    for tpl in ['colorful','unicorn']:
        pg.click('#pres'); pg.wait_for_selector('[data-pf="gslides"]'); pg.click('[data-pf="gslides"]'); pg.click(f'[data-pt="{tpl}"]'); pg.click('#pgo')
        pg.wait_for_selector('text=Saved to Google Slides', timeout=60000)
        u=[x for x in uploads if x[0] in ('multipart','resumable-put')][-1]
        print('3', tpl, '->', u[0], u[1]['mimeType'], '| size MB', round(len(u[2])/1048576,2), '| valid pptx:', ok_file(u[2],'slides')); pg.click('[data-close]')
    pg.screenshot(path='gt-pres.png')
    # 4. expired access: Google says 401, app signs in again and finishes
    fail401['n']=1; pg.click('#back'); pg.click('[data-open="p1"]'); pg.click('#export'); pg.wait_for_selector('#wgoogle'); pg.click('#wgoogle')
    pg.wait_for_selector('text=Saved to Google Docs', timeout=20000)
    print('4 progress note after expired access ->', uploads[-1][1]['mimeType'], uploads[-1][1]['name'], '| token used:', uploads[-1][3])
    # 5. sign-in cancelled
    pg.goto('http://127.0.0.1:8820/index.html#error=access_denied&state=x'); pg.wait_for_timeout(500)
    print('5 cancelled ->', pg.locator('.toast').all_inner_texts(), '| hash cleared:', '#' not in pg.url)
    b.close()
print('sign-ins:', [l for l in log if l[0]=='signin'][:1], 'total', len([l for l in log if l[0]=='signin']))
print('errors', errs)
