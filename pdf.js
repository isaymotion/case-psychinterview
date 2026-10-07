/* ---------- Case presentation as PDF ----------
   Draws the same slides the PowerPoint file has, on the iPad, and saves them as a PDF.
   Each slide is drawn as a picture: the template's artwork (a background image made once with
   tools/make_backgrounds.js), then the boxes, tables and text the generator laid out.
   Text uses fonts that ship with the app (fonts/), so it looks the same on every iPad and offline.
   No libraries. Text in the PDF is part of the picture, so it cannot be selected or searched. */
const CasePDF = (() => {
'use strict';

const PX = 150;                 // pixels per inch of slide (a widescreen slide becomes 2000 x 1125)
const FAM = { body:'CaseBody', head:'CaseHead', title:'CaseTitle' };
const STACK = f => `"${f}", "Helvetica Neue", Helvetica, Arial, sans-serif`;

/* ----- fonts ----- */
let fontsReady = null;
function loadFonts(base){
  if(fontsReady) return fontsReady;
  const list = [
    [FAM.body,'body-regular',{}], [FAM.body,'body-bold',{weight:'700'}], [FAM.body,'body-italic',{style:'italic'}], [FAM.body,'body-bolditalic',{weight:'700', style:'italic'}],
    [FAM.head,'head-bold',{weight:'100 900'}], [FAM.title,'title-black',{weight:'100 900'}], [FAM.title,'title-blackitalic',{weight:'100 900', style:'italic'}]
  ];
  fontsReady = Promise.all(list.map(([fam, file, desc]) => {
    const f = new FontFace(fam, `url(${base}${file}.woff) format("woff")`, desc);
    return f.load().then(x => { document.fonts.add(x); }).catch(() => {});   // a missing font falls back to the iPad's own
  }));
  return fontsReady;
}

/* ----- colors: theme colors with the same light/dark changes PowerPoint applies ----- */
function hexToHsl(h){
  const r=parseInt(h.slice(0,2),16)/255, g=parseInt(h.slice(2,4),16)/255, b=parseInt(h.slice(4,6),16)/255;
  const mx=Math.max(r,g,b), mn=Math.min(r,g,b), l=(mx+mn)/2; let hh=0, s=0;
  if(mx!==mn){ const d=mx-mn; s = l>0.5 ? d/(2-mx-mn) : d/(mx+mn);
    hh = mx===r ? (g-b)/d + (g<b?6:0) : mx===g ? (b-r)/d + 2 : (r-g)/d + 4; hh/=6; }
  return [hh, s, l];
}
function hslToHex(h, s, l){
  const f = (p,q,t) => { if(t<0) t+=1; if(t>1) t-=1; return t<1/6 ? p+(q-p)*6*t : t<1/2 ? q : t<2/3 ? p+(q-p)*(2/3-t)*6 : p; };
  let r,g,b; if(s===0){ r=g=b=l; } else { const q = l<0.5 ? l*(1+s) : l+s-l*s, p = 2*l-q; r=f(p,q,h+1/3); g=f(p,q,h); b=f(p,q,h-1/3); }
  return '#'+[r,g,b].map(x=>Math.round(Math.min(1,Math.max(0,x))*255).toString(16).padStart(2,'0')).join('');
}
const MODS = { tint:[0.2,0.8], soft:[0.4,0.6], dark:[0.75,0], line:[0.85,0], muted:[0.65,0.35] };
function color(c, theme){
  const [v, mod] = String(c || 'tx1').split(':');
  const key = { tx1:'dk1', tx2:'dk2', bg1:'lt1', bg2:'lt2' }[v] || v;
  const hex = (theme[key] || (/^[0-9a-f]{6}$/i.test(v) ? v : '000000')).toUpperCase();
  if(!MODS[mod]) return '#'+hex;
  const [h,s,l] = hexToHsl(hex), [m,o] = MODS[mod];
  return hslToHex(h, s, Math.min(1, l*m + o));
}

/* ----- text ----- */
function fontOf(r, def){
  const fam = r.font==='head' ? FAM.head : r.font==='head-template' || r.font==='+mj-lt' ? FAM.title : r.font ? FAM.body : def;
  const weight = fam===FAM.body ? (r.b ? 700 : 400) : 900;
  return { css: `${r.i?'italic ':''}${weight} SIZEpx ${STACK(fam)}`, fam };
}
// Lay paragraphs out in a width (inches); returns lines with their runs and positions
function layout(g, paras, widthIn, def){
  const lines = [];
  paras.forEach((p, pi) => {
    const runs = (p.runs||[]).filter(r => r.t!=null && r.t!=='');
    const size0 = (runs[0] && runs[0].sz) || def.sz;
    const indent = p.bullet ? 0.25 : 0, avail = Math.max(0.2, widthIn - indent);
    const tokens = [];
    runs.forEach(r => {
      const sz = r.sz || def.sz, f = fontOf(r, def.fam), col = r.color || def.color;
      String(r.t).split(/(\s+)/).filter(x=>x!=='').forEach(t => tokens.push({ t, sz, font:f.css.replace('SIZE', String(sz/72*PX)), color:col, space:/^\s+$/.test(t) }));
    });
    const width = tk => { g.font = tk.font; return g.measureText(tk.t).width / PX; };
    let cur = [], curW = 0, first = true;
    const push = (last) => {
      while(cur.length && cur[cur.length-1].space) { curW -= cur[cur.length-1].w; cur.pop(); }
      const sz = Math.max(size0, ...cur.map(x=>x.sz));
      lines.push({ toks:cur, w:curW, sz, lh: sz/72 * 1.2 * (p.line ? p.line/100000 : def.lnSpc), indent,
        align: p.align || def.align, bullet: first && p.bullet, before: first ? (p.before||0)/72 : 0, after: last ? (p.after||0)/72 : 0, bulletFont: tokens[0] ? tokens[0].font : '' });
      cur = []; curW = 0; first = false;
    };
    tokens.forEach(tk => {
      tk.w = width(tk);
      if(tk.space && !cur.length) return;
      if(!tk.space && curW + tk.w > avail && cur.length){ push(false); }
      if(!tk.space && tk.w > avail){   // a word longer than the line: break it
        let s = tk.t;
        while(s.length){ let n = s.length; while(n>1 && width({ ...tk, t:s.slice(0,n) }) > avail - curW) n--;
          const part = { ...tk, t:s.slice(0,n) }; part.w = width(part); cur.push(part); curW += part.w; s = s.slice(n); if(s.length) push(false); }
        return;
      }
      cur.push(tk); curW += tk.w;
    });
    push(true);
    if(!runs.length && lines.length) lines[lines.length-1].empty = true;
  });
  return lines;
}
function drawText(g, paras, box, inset, anchor, def, theme){
  if(!paras || !paras.length) return;
  const x = box.x + inset[0], w = box.w - inset[0] - inset[2], top = box.y + inset[1], h = box.h - inset[1] - inset[3];
  const lines = layout(g, paras, w, def);
  const total = lines.reduce((a,l)=>a + l.before + l.lh + l.after, 0);
  let y = anchor==='ctr' ? top + (h-total)/2 : anchor==='b' ? top + h - total : top;
  lines.forEach(l => {
    y += l.before;
    const base = y + l.lh - l.sz/72 * 0.25;   // baseline: a quarter of the letter size above the bottom of the line
    let lx = x + l.indent;
    if(l.align==='ctr') lx = x + l.indent + (w - l.indent - l.w)/2; else if(l.align==='r') lx = x + w - l.w;
    if(l.bullet && l.toks.length){ g.font = l.toks[0].font; g.fillStyle = color(l.toks[0].color, theme); g.fillText('•', (x)*PX, base*PX); }
    l.toks.forEach(tk => { g.font = tk.font; g.fillStyle = color(tk.color, theme); g.fillText(tk.t, lx*PX, base*PX); lx += tk.w; });
    y += l.lh + l.after;
  });
}

/* ----- shapes ----- */
function path(g, geom, x, y, w, h, adj){
  g.beginPath();
  if(geom==='ellipse'){ g.ellipse((x+w/2)*PX, (y+h/2)*PX, w/2*PX, h/2*PX, 0, 0, Math.PI*2); return; }
  if(geom==='roundRect'){
    const r = Math.min(w,h) * (adj!=null ? adj/100000 : 0.16667) * PX, X=x*PX, Y=y*PX, W=w*PX, H=h*PX;
    g.moveTo(X+r, Y); g.lineTo(X+W-r, Y); g.arcTo(X+W, Y, X+W, Y+r, r); g.lineTo(X+W, Y+H-r); g.arcTo(X+W, Y+H, X+W-r, Y+H, r);
    g.lineTo(X+r, Y+H); g.arcTo(X, Y+H, X, Y+H-r, r); g.lineTo(X, Y+r); g.arcTo(X, Y, X+r, Y, r); g.closePath(); return;
  }
  g.rect(x*PX, y*PX, w*PX, h*PX);
}
function drawShape(g, o, theme){
  if(o.fill || o.line){
    path(g, o.geom, o.x, o.y, o.w, o.h, o.adj);
    if(o.fill){ g.fillStyle = color(o.fill, theme); g.fill(); }
    if(o.line){ g.strokeStyle = color(o.line, theme); g.lineWidth = Math.max(1, (o.lineW||0.014)*PX); g.stroke(); }
  }
  if(o.paras) drawText(g, o.paras, o, o.inset || [0.14,0.1,0.14,0.1], o.anchor || 't', { sz:14, fam:FAM.body, color:'tx1', align:'l', lnSpc:1 }, theme);
}
function drawTable(g, o, theme){
  let y = o.y;
  o.rows.forEach(r => {
    let x = o.x;
    r.cells.forEach((paras, i) => {
      const w = o.cols[i];
      g.fillStyle = color((r.fill && r.fill[i]) || 'bg1', theme); g.fillRect(x*PX, y*PX, w*PX, r.h*PX);
      drawText(g, paras, { x, y, w, h:r.h }, [0.1,0.06,0.1,0.06], 't', { sz:14, fam:FAM.body, color:'tx1', align:'l', lnSpc:1 }, theme);
      x += w;
    });
    y += r.h;
  });
  // cell borders
  g.strokeStyle = color('bg1:line', theme); g.lineWidth = Math.max(1, 0.75/72*PX);
  const W = o.cols.reduce((a,b)=>a+b,0); let yy = o.y;
  g.beginPath(); g.moveTo(o.x*PX, yy*PX); g.lineTo((o.x+W)*PX, yy*PX);
  o.rows.forEach(r => { yy += r.h; g.moveTo(o.x*PX, yy*PX); g.lineTo((o.x+W)*PX, yy*PX); });
  let xx = o.x; g.moveTo(xx*PX, o.y*PX); g.lineTo(xx*PX, yy*PX);
  o.cols.forEach(c => { xx += c; g.moveTo(xx*PX, o.y*PX); g.lineTo(xx*PX, yy*PX); });
  g.stroke();
}

/* ----- one slide ----- */
const imgCache = {};
function loadImage(url){
  if(!imgCache[url]) imgCache[url] = new Promise(res => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; });
  return imgCache[url];
}
async function drawSlide(deck, sl, bgBase){
  const c = document.createElement('canvas'); c.width = Math.round(deck.W*PX); c.height = Math.round(deck.H*PX);
  const g = c.getContext('2d');
  g.fillStyle = color(deck.bg, deck.theme); g.fillRect(0, 0, c.width, c.height);
  const bg = bgBase ? await loadImage(bgBase + sl.layout + '.png') : null;
  if(bg) g.drawImage(bg, 0, 0, c.width, c.height);
  g.textBaseline = 'alphabetic';
  for(const it of sl.items){
    if(it.kind==='shape') drawShape(g, it.o, deck.theme);
    else if(it.kind==='table') drawTable(g, it.o, deck.theme);
    else if(it.kind==='ph'){
      const inf = it.info, b = inf.box; if(!b) continue;
      if(inf.fill){ path(g, inf.geom, b.x, b.y, b.w, b.h); g.fillStyle = color(inf.fill, deck.theme); g.fill(); }
      if(deck.badgeIdx!=null && String(it.ph.idx)===String(deck.badgeIdx)) continue;   // the circle's own text is hidden by the template
      drawText(g, it.paras, b, inf.inset, inf.anchor, { sz:18, fam:FAM.title, color:'tx1', align:inf.align, lnSpc:inf.lnSpc }, deck.theme);
    }
  }
  const blob = await new Promise(res => c.toBlob(res, 'image/jpeg', 0.86));
  c.width = c.height = 0;   // free the iPad's memory before the next slide
  return { jpeg: new Uint8Array(await blob.arrayBuffer()), w: Math.round(deck.W*PX), h: Math.round(deck.H*PX) };
}

/* ----- the PDF file: one picture per page ----- */
function pdfString(s){
  if(/^[\x20-\x7E]*$/.test(s)) return '(' + s.replace(/[\\()]/g, m => '\\'+m) + ')';
  let hex = 'FEFF'; for(const ch of s){ const cp = ch.codePointAt(0);
    const u = cp>0xFFFF ? [0xD800+((cp-0x10000)>>10), 0xDC00+((cp-0x10000)&0x3FF)] : [cp]; u.forEach(x=>{ hex += x.toString(16).toUpperCase().padStart(4,'0'); }); }
  return '<'+hex+'>';
}
function buildPDF(pages, Wpt, Hpt, title){
  const enc = new TextEncoder(), chunks = [], offs = []; let size = 0;
  const add = x => { const b = typeof x==='string' ? enc.encode(x) : x; chunks.push(b); size += b.length; };
  const obj = (n, body) => { offs[n] = size; add(`${n} 0 obj\n`); body(); add('\nendobj\n'); };
  add('%PDF-1.4\n'); add(new Uint8Array([0x25,0xE2,0xE3,0xCF,0xD3,0x0A]));
  const n = pages.length, pageObj = i => 4 + i*3;
  obj(1, () => add('<< /Type /Catalog /Pages 2 0 R >>'));
  obj(2, () => add(`<< /Type /Pages /Count ${n} /Kids [${pages.map((_,i)=>pageObj(i)+' 0 R').join(' ')}] >>`));
  obj(3, () => add(`<< /Title ${pdfString(title||'Case presentation')} /Producer (Case & MSE app) /CreationDate (D:${new Date().toISOString().replace(/[-:T]/g,'').slice(0,14)}) >>`));
  pages.forEach((p, i) => {
    const po = pageObj(i), co = po+1, io = po+2;
    obj(po, () => add(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${Wpt} ${Hpt}] /Resources << /XObject << /Im0 ${io} 0 R >> >> /Contents ${co} 0 R >>`));
    const content = `q ${Wpt} 0 0 ${Hpt} 0 0 cm /Im0 Do Q`;
    obj(co, () => { add(`<< /Length ${content.length} >>\nstream\n`); add(content); add('\nendstream'); });
    obj(io, () => { add(`<< /Type /XObject /Subtype /Image /Width ${p.w} /Height ${p.h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${p.jpeg.length} >>\nstream\n`); add(p.jpeg); add('\nendstream'); });
  });
  const total = 4 + n*3, xref = size;
  let x = `xref\n0 ${total}\n0000000000 65535 f \n`;
  for(let k=1;k<total;k++) x += String(offs[k]).padStart(10,'0') + ' 00000 n \n';
  add(x + `trailer\n<< /Size ${total} /Root 1 0 R /Info 3 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  const out = new Uint8Array(size); let o = 0; chunks.forEach(c => { out.set(c, o); o += c.length; });
  return out;
}

/* Public: deck comes from CaseSlides.generate(); opts { backgrounds, fonts, title, onProgress } */
async function render(deck, opts){
  opts = opts || {};
  if(opts.fonts) await loadFonts(opts.fonts);
  const pages = [];
  for(let i=0;i<deck.slides.length;i++){
    pages.push(await drawSlide(deck, deck.slides[i], opts.backgrounds));
    if(opts.onProgress) opts.onProgress(i+1, deck.slides.length);
  }
  return buildPDF(pages, Math.round(deck.W*72*100)/100, Math.round(deck.H*72*100)/100, opts.title);
}

return { render, _test:{ buildPDF, color } };
})();
if (typeof module !== 'undefined') module.exports = CasePDF;
