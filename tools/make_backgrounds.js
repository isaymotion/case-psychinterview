#!/usr/bin/env node
/* Draws each layout of a slide template without its text boxes, as a picture the app uses as the
   background when it makes PDF slides on the iPad (it cannot draw PowerPoint artwork itself).
   Needs LibreOffice and Poppler (pdftoppm) on the computer that runs it.

     node tools/make_backgrounds.js colorful
   (the template's id in TEMPLATES in slides.js; the pictures go to its pdf.backgrounds folder)
*/
const fs = require('fs'), path = require('path'), os = require('os'), { execFileSync } = require('child_process');
const CaseSlides = require('../slides.js');
const [,, id, soffice = 'soffice'] = process.argv;
const cfg = CaseSlides.TEMPLATES.find(t => t.id===id);
if(!cfg || !cfg.pdf){ console.error('usage: node tools/make_backgrounds.js <template id> [soffice command]'); process.exit(1); }
const root = path.join(__dirname, '..'), tplPath = path.join(root, cfg.file), outDir = path.join(root, cfg.pdf.backgrounds);
(async () => {
  const buf = fs.readFileSync(tplPath);
  const tpl = await CaseSlides._test.loadTemplate(buf.buffer.slice(buf.byteOffset, buf.byteOffset+buf.length), cfg);
  // Only the layouts the generator uses
  const used = [...new Set([tpl.L.title, tpl.L.content, tpl.L.section, tpl.L.quote, tpl.L.end, ...tpl.L.parts].filter(Boolean))];
  const dec = new TextDecoder(), enc = new TextEncoder();
  // Placeholders (titles, text, the badge circle) are drawn by the app, so leave them out of the picture
  for(const k of [...tpl.files.keys()]) if(/^ppt\/(slideLayouts|slideMasters)\/[^/]+\.xml$/.test(k)){
    const x = dec.decode(tpl.files.get(k)).replace(/<p:sp>[\s\S]*?<\/p:sp>/g, m => /<p:ph\b/.test(m) ? '' : m);
    tpl.files.set(k, enc.encode(x));
  }
  const empty = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>';
  const rendered = used.map(l => ({ xml: empty, layout: l.path, notes: '' }));
  const bytes = CaseSlides._test.assemble(tpl, rendered, { notes:false, title:'Backgrounds' });
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bg-'));
  fs.writeFileSync(path.join(tmp, 'bg.pptx'), Buffer.from(bytes));
  execFileSync(soffice.split(' ')[0], [...soffice.split(' ').slice(1), '--headless', '--convert-to', 'pdf', '--outdir', tmp, path.join(tmp, 'bg.pptx')], { stdio:'ignore' });
  const PX = 150;   // pixels per inch, as in pdf.js: 2000 pixels across a widescreen slide
  execFileSync('pdftoppm', ['-png', '-scale-to-x', String(Math.round(tpl.W*PX)), '-scale-to-y', String(Math.round(tpl.H*PX)), path.join(tmp, 'bg.pdf'), path.join(tmp, 'p')]);
  fs.mkdirSync(outDir, { recursive:true });
  const pages = fs.readdirSync(tmp).filter(f => /^p-\d+\.png$/.test(f)).sort((a,b) => parseInt(a.slice(2)) - parseInt(b.slice(2)));
  for(const f of fs.readdirSync(outDir)) if(/\.png$/.test(f)) fs.unlinkSync(path.join(outDir, f));
  pages.forEach((f, i) => { const name = path.basename(used[i].path, '.xml') + '.png'; fs.copyFileSync(path.join(tmp, f), path.join(outDir, name)); });
  console.log(`${pages.length} backgrounds in ${outDir}`);
})().catch(e => { console.error(e); process.exit(1); });
