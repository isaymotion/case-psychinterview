import json,sys
# usage: para_replace.py READ_RESULT SPEC.json  -> prints {"rev":..,"requests":[..]}
d=json.load(open(sys.argv[1])); c=d['content']; c=json.loads(c) if isinstance(c,str) else c
spec=json.load(open(sys.argv[2]))
paras=[]
def walk(els):
    for e in els:
        if 'paragraph' in e:
            t=''.join(r.get('textRun',{}).get('content','') for r in e['paragraph']['elements'])
            paras.append((e['startIndex'],e['endIndex'],t))
        if 'table' in e:
            for row in e['table']['tableRows']:
                for cell in row['tableCells']: walk(cell['content'])
walk(c['tabs'][0]['documentTab']['body']['content'])
L=lambda s: len(s.encode('utf-16-le'))//2
jobs=[]
for sp in spec:
    hits=[p for p in paras if p[2].startswith(sp['prefix'])]
    if len(hits)!=1: sys.exit(f"prefix {sp['prefix']!r} matched {len(hits)}")
    s,e,_=hits[0]; jobs.append((s,e,sp))
jobs.sort(key=lambda j:-j[0])
R=[]
for s,e,sp in jobs:
    if e-1>s: R.append({"deleteContentRange":{"range":{"startIndex":s,"endIndex":e-1,"tabId":"t.0"}}})
    R.append({"insertText":{"location":{"index":s,"tabId":"t.0"},"text":sp['text']}})
    R.append({"updateTextStyle":{"range":{"startIndex":s,"endIndex":s+L(sp['text']),"tabId":"t.0"},"textStyle":{"italic":False,"bold":bool(sp.get('bold')),"foregroundColor":{"color":{"rgbColor":{"red":0,"green":0,"blue":0}}}},"fields":"italic,bold,foregroundColor"}})
    if sp.get('italicprefix'):
        R.append({"updateTextStyle":{"range":{"startIndex":s,"endIndex":s+L(sp['italicprefix']),"tabId":"t.0"},"textStyle":{"italic":True},"fields":"italic"}})
    if sp.get('boldprefix'):
        R.append({"updateTextStyle":{"range":{"startIndex":s,"endIndex":s+L(sp['boldprefix']),"tabId":"t.0"},"textStyle":{"bold":True},"fields":"bold"}})
    for red in sp.get('red',[]):
        i=sp['text'].index(red); a=s+L(sp['text'][:i])
        R.append({"updateTextStyle":{"range":{"startIndex":a,"endIndex":a+L(red),"tabId":"t.0"},"textStyle":{"italic":True,"foregroundColor":{"color":{"rgbColor":{"red":0.753,"green":0,"blue":0}}}},"fields":"italic,foregroundColor"}})
print(json.dumps({"rev":c['revisionId'],"requests":R},ensure_ascii=False))
