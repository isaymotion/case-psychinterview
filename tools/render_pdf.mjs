// Render an HTML handout to an A4 PDF with a confidential footer and page numbers.
// usage: node render_pdf.mjs handout.html Out.pdf "Footer text"
import { createRequire } from 'module';
import path from 'path';
const { chromium } = createRequire(import.meta.url)('playwright');
const [,, IN, OUT, FOOT = 'CONFIDENTIAL, de-identified · do not forward'] = process.argv;
const b = await chromium.launch(); const p = await b.newPage();
await p.goto('file://' + path.resolve(IN));
await p.pdf({ path: OUT, format: 'A4', printBackground: true, displayHeaderFooter: true, headerTemplate: '<span></span>',
  footerTemplate: `<div style="font-size:7px;width:100%;text-align:center;color:#666">${FOOT} · Page <span class=pageNumber></span> of <span class=totalPages></span></div>`,
  margin: { top: '10mm', bottom: '11mm', left: '11mm', right: '11mm' } });
await b.close(); console.log('wrote', OUT);
