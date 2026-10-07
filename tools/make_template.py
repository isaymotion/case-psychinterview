#!/usr/bin/env python3
"""Turn any PowerPoint deck into a slide template for the case presentation generator.

Keeps the deck's design (slide masters, layouts, theme colors and fonts, background art) and
removes its slides, speaker notes, comments and document metadata, so the template file is
small and carries no content from the original deck.

    python3 tools/make_template.py "My deck.pptx" templates/mytemplate.pptx
"""
import re, sys, zipfile, posixpath

def rels_of(part):
    d, f = posixpath.split(part)
    return posixpath.join(d, '_rels', f + '.rels')

def main(src, dst):
    z = zipfile.ZipFile(src)
    files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    drop = lambda n: re.match(r'ppt/(slides|notesSlides|comments)/', n) or re.match(r'ppt/(commentAuthors|authors)\.xml', n) \
        or n.startswith('docMetadata/') or n in ('docProps/custom.xml', 'docProps/thumbnail.jpeg')
    for n in [n for n in files if drop(n)]:
        del files[n]
    pres = files['ppt/presentation.xml'].decode()
    pres = re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>|<p:sldIdLst\s*/>', '', pres, flags=re.S)
    pres = re.sub(r'<p:custShowLst>.*?</p:custShowLst>', '', pres, flags=re.S)
    pres = re.sub(r'<p:ext uri="\{521415D9-36F7-43E2-AB2F-B90AF26B5E84\}">.*?</p:ext>', '', pres, flags=re.S)
    files['ppt/presentation.xml'] = pres.encode()
    # drop relationships whose target is gone
    for rp in [n for n in files if n.endswith('.rels')]:
        x = files[rp].decode()
        base = posixpath.dirname(posixpath.dirname(rp))
        def keep(m):
            t = re.search(r'Target="([^"]*)"', m.group(0)).group(1)
            if 'TargetMode="External"' in m.group(0): return m.group(0)
            full = t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(base, t))
            return m.group(0) if full in files else ''
        files[rp] = re.sub(r'<Relationship\b[^>]*?/>', keep, x).encode()
    # keep only parts still reachable from the package root
    reach, stack = set(), ['_rels/.rels']
    def visit(part):
        if part in reach or part not in files: return
        reach.add(part)
        rp = rels_of(part)
        if rp in files:
            reach.add(rp)
            base = posixpath.dirname(part)
            for t, ext in re.findall(r'Target="([^"]*)"([^>]*)', files[rp].decode()):
                if 'External' in ext: continue
                visit(t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(base, t)))
    reach.add('_rels/.rels')
    for t in re.findall(r'Target="([^"]*)"', files['_rels/.rels'].decode()):
        visit(t.lstrip('/'))
    reach.add('[Content_Types].xml')
    files = {n: b for n, b in files.items() if n in reach}
    ct = files['[Content_Types].xml'].decode()
    ct = re.sub(r'<Override PartName="/([^"]+)"[^>]*/>', lambda m: m.group(0) if m.group(1) in files else '', ct)
    files['[Content_Types].xml'] = ct.encode()
    core = files.get('docProps/core.xml')
    if core:
        files['docProps/core.xml'] = re.sub(rb'<cp:lastModifiedBy>.*?</cp:lastModifiedBy>|<dc:creator>.*?</dc:creator>', b'', core)
    # stored without compression so older iPads can read it (the app has no unzip library)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as out:
        out.writestr('[Content_Types].xml', files.pop('[Content_Types].xml'))
        for n in sorted(files):
            out.writestr(n, files[n])
    print(f'{dst}: {len(files)+1} parts kept')

if __name__ == '__main__':
    main(*sys.argv[1:3])
