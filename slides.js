/* ---------- Case presentation slides (.pptx) ----------
   Fills a PowerPoint template's own slide layouts with the case data, so the deck keeps the
   template's backgrounds, colors and fonts. No libraries; runs offline on the iPad.

   To add a template: run  python3 tools/make_template.py "Deck.pptx" templates/<name>.pptx
   (keeps the design, removes the slides), add a line to TEMPLATES below, and add the file to
   FILES in sw.js. Any ordinary PowerPoint deck works: the generator looks for the standard
   layouts (Title Slide, Title and Content, Section Header, Quote, Thank You).

   The slide order follows CASE_FORMAT: change it there to match a department's format.
   Sections added to the case template later are placed automatically, so the deck keeps up
   with changes to the case format. */
const CaseSlides = (() => {
'use strict';

const TEMPLATES = [
  { id:'colorful', name:'Colorful', note:'Cream background, bold color lines and dots',
    file:'templates/colorful.pptx',
    bodyFont:'Calibri', headFont:'Cambria',   // fonts for the text the generator writes; titles keep the template's font
    titleFont:'Arial Black',                   // the template's title font, used to size titles so they fit
    area:{ x:0.8, y:1.95, w:11.73, h:4.72 },  // free space under the title bar, in inches
    badge:{ idx:13, color:'bg2', size:26 },    // the colored circle beside the title shows the slide's first letter
    footer:false,                              // this design has no footer strip
    // each part of the presentation uses its own layout, so the circle changes color: red, blue, orange, green
    partLayouts:['Title and Content','Title and Content - Chart','Title and Content - Table','2_Title and Content'],
    partColors:['accent1','accent2','accent4','accent3'],
    titleInfo:{ x:2.98, y:4.68, w:7.6, h:0.62 },   // patient line under the title on the first slide
    confidential:{ x:0.8, y:6.98, w:8, h:0.3 } }   // confidentiality line at the bottom of the first slide
];

/* Parts of the presentation, in order. Section ids are the ones in the case template. */
const CASE_FORMAT = [
  { part:'History', sections:['idd','cc','hpi','ros','pph','safety','sub','med','fam','soc'] },
  { part:'Mental status examination', sections:['mse'] },
  { part:'Examination and work-up', sections:['pe','labs'] },
  { part:'Formulation and plan', sections:['form','dx','risk','plan'] }
];

const EMU = 914400, E = n => Math.round(n*EMU);
const enc = new TextEncoder(), dec = new TextDecoder();
const S = v => (typeof v==='string' ? v.trim() : '');
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g,'');
const NS = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"';
const REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const XMLH = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';

/* ===== ZIP: read (stored or deflated) and write (stored) ===== */
const CRC_T = (()=>{ const t=new Uint32Array(256); for(let n=0;n<256;n++){ let c=n; for(let k=0;k<8;k++) c = c&1 ? 0xEDB88320^(c>>>1) : c>>>1; t[n]=c>>>0; } return t; })();
const crc32 = b => { let c=0xFFFFFFFF; for(let i=0;i<b.length;i++) c = CRC_T[(c^b[i])&0xFF]^(c>>>8); return (c^0xFFFFFFFF)>>>0; };

async function unzip(buf){
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  let e=-1; for(let i=u8.length-22; i>=Math.max(0,u8.length-66000); i--){ if(dv.getUint32(i,true)===0x06054b50){ e=i; break; } }
  if(e<0) throw new Error('not-pptx');
  const count=dv.getUint16(e+10,true); let p=dv.getUint32(e+16,true);
  const out = new Map();
  for(let k=0;k<count;k++){
    if(dv.getUint32(p,true)!==0x02014b50) break;
    const method=dv.getUint16(p+10,true), csize=dv.getUint32(p+20,true), nlen=dv.getUint16(p+28,true), xlen=dv.getUint16(p+30,true), clen=dv.getUint16(p+32,true), off=dv.getUint32(p+42,true);
    const name = dec.decode(u8.subarray(p+46, p+46+nlen));
    p += 46+nlen+xlen+clen;
    if(name.endsWith('/')) continue;
    const start = off+30+dv.getUint16(off+26,true)+dv.getUint16(off+28,true);
    const raw = u8.subarray(start, start+csize);
    if(method===0) out.set(name, raw.slice());
    else if(method===8){
      if(typeof DecompressionStream==='undefined') throw new Error('old-ios');
      const stream = new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      out.set(name, new Uint8Array(await new Response(stream).arrayBuffer()));
    } else throw new Error('unsupported');
  }
  return out;
}

function zip(files){ // files: Map name -> Uint8Array | string
  const now=new Date();
  const dtime=(now.getHours()<<11)|(now.getMinutes()<<5)|(now.getSeconds()>>1);
  const ddate=((now.getFullYear()-1980)<<9)|((now.getMonth()+1)<<5)|now.getDate();
  const names = [...files.keys()].sort((a,b)=> a==='[Content_Types].xml' ? -1 : b==='[Content_Types].xml' ? 1 : 0);
  const chunks=[], central=[]; let off=0;
  for(const name of names){
    const v=files.get(name), nb=enc.encode(name), db = typeof v==='string' ? enc.encode(v) : v, crc=crc32(db);
    const h=new DataView(new ArrayBuffer(30));
    h.setUint32(0,0x04034b50,true); h.setUint16(4,20,true); h.setUint16(6,0x0800,true); h.setUint16(8,0,true);
    h.setUint16(10,dtime,true); h.setUint16(12,ddate,true); h.setUint32(14,crc,true); h.setUint32(18,db.length,true); h.setUint32(22,db.length,true);
    h.setUint16(26,nb.length,true); h.setUint16(28,0,true);
    chunks.push(new Uint8Array(h.buffer), nb, db);
    const c=new DataView(new ArrayBuffer(46));
    c.setUint32(0,0x02014b50,true); c.setUint16(4,20,true); c.setUint16(6,20,true); c.setUint16(8,0x0800,true); c.setUint16(10,0,true);
    c.setUint16(12,dtime,true); c.setUint16(14,ddate,true); c.setUint32(16,crc,true); c.setUint32(20,db.length,true); c.setUint32(24,db.length,true);
    c.setUint16(28,nb.length,true); c.setUint32(42,off,true);
    central.push(new Uint8Array(c.buffer), nb);
    off += 30+nb.length+db.length;
  }
  const csize=central.reduce((a,b)=>a+b.length,0);
  const e=new DataView(new ArrayBuffer(22));
  e.setUint32(0,0x06054b50,true); e.setUint16(8,names.length,true); e.setUint16(10,names.length,true); e.setUint32(12,csize,true); e.setUint32(16,off,true);
  const all=[...chunks,...central,new Uint8Array(e.buffer)], out=new Uint8Array(all.reduce((a,b)=>a+b.length,0));
  let q=0; for(const a of all){ out.set(a,q); q+=a.length; }
  return out;
}

/* ===== Package helpers ===== */
const relsPath = part => { const i=part.lastIndexOf('/'); return part.slice(0,i+1)+'_rels/'+part.slice(i+1)+'.rels'; };
function resolve(fromPart, target){
  if(target.startsWith('/')) return target.slice(1);
  const parts = fromPart.split('/'); parts.pop();
  for(const seg of target.split('/')){ if(seg==='..') parts.pop(); else if(seg!=='.' && seg!=='') parts.push(seg); }
  return parts.join('/');
}
function readRels(files, part){
  const b = files.get(relsPath(part)); if(!b) return [];
  const x = dec.decode(b), out=[];
  x.replace(/<Relationship\b([^>]*?)\/?>/g, (m,a)=>{
    const g = k => { const r=a.match(new RegExp('\\b'+k+'="([^"]*)"')); return r?r[1]:''; };
    out.push({ id:g('Id'), type:g('Type'), target:g('Target'), external:g('TargetMode')==='External' });
    return m;
  });
  return out;
}
const attr = (tag, k) => { const m=tag.match(new RegExp('\\b'+k+'="([^"]*)"')); return m?m[1]:null; };

/* Placeholders of a layout or master: type, idx and position (inches) when given */
function placeholders(xml){
  const out=[];
  const re = /<p:sp>([\s\S]*?)<\/p:sp>/g; let m;
  while((m=re.exec(xml))){
    const sp=m[1], ph=sp.match(/<p:ph\b[^>]*>/); if(!ph) continue;
    const off=sp.match(/<a:off x="(-?\d+)" y="(-?\d+)"\s*\/>\s*<a:ext cx="(\d+)" cy="(\d+)"/);
    out.push({ type: attr(ph[0],'type') || 'obj', idx: attr(ph[0],'idx'), rawType: attr(ph[0],'type'),
      box: off ? { x:+off[1]/EMU, y:+off[2]/EMU, w:+off[3]/EMU, h:+off[4]/EMU } : null });
  }
  return out;
}

/* ===== Template ===== */
async function loadTemplate(buf, cfg){
  cfg = cfg || {};
  const files = await unzip(buf);
  const T = t => files.has(t) ? dec.decode(files.get(t)) : '';
  if(!files.has('ppt/presentation.xml')) throw new Error('not-pptx');
  // Remove the template's own slides; keep masters, layouts, theme and media
  for(const k of [...files.keys()]) if(/^ppt\/(slides|notesSlides|comments)\//.test(k) || /^ppt\/(commentAuthors|authors)\.xml$/.test(k)) files.delete(k);
  let pres = T('ppt/presentation.xml');
  pres = pres.replace(/<p:sldIdLst>[\s\S]*?<\/p:sldIdLst>|<p:sldIdLst\s*\/>/,'').replace(/<p:custShowLst>[\s\S]*?<\/p:custShowLst>/,'')
             .replace(/<p:ext uri="\{521415D9-36F7-43E2-AB2F-B90AF26B5E84\}">[\s\S]*?<\/p:ext>/,'');   // slide sections
  files.set('ppt/presentation.xml', enc.encode(pres));
  let prels = T('ppt/_rels/presentation.xml.rels').replace(/<Relationship\b[^>]*Type="[^"]*\/(slide|commentAuthors|authors)"[^>]*\/>/g,'');
  files.set('ppt/_rels/presentation.xml.rels', enc.encode(prels));

  const pr = readRels(files, 'ppt/presentation.xml');
  const masterRel = pr.find(r=>/\/slideMaster$/.test(r.type)); if(!masterRel) throw new Error('not-pptx');
  const master = resolve('ppt/presentation.xml', masterRel.target);
  const notesRel = pr.find(r=>/\/notesMaster$/.test(r.type));
  const masterPh = placeholders(T(master));
  const layouts = readRels(files, master).filter(r=>/\/slideLayout$/.test(r.type)).map(r=>{
    const path = resolve(master, r.target), x = T(path);
    const tag = (x.match(/<p:sldLayout\b[^>]*>/)||[''])[0];
    return { path, name: (x.match(/<p:cSld\b[^>]*name="([^"]*)"/)||[])[1] || '', type: attr(tag,'type') || '', ph: placeholders(x) };
  });
  if(!layouts.length) throw new Error('not-pptx');
  const sz = pres.match(/<p:sldSz cx="(\d+)" cy="(\d+)"/);
  const W = sz ? +sz[1]/EMU : 13.333, H = sz ? +sz[2]/EMU : 7.5;

  const find = (...tests) => { for(const t of tests){ const l=layouts.find(t); if(l) return l; } return null; };
  const byName = re => l => re.test(l.name.trim());
  const L = {};
  L.title   = find(l=>l.type==='title', byName(/^title slide$/i)) || layouts[0];
  L.content = find(byName(/^title and content$/i), l=>l.type==='obj', byName(/^title only$/i), l=>l.type==='titleOnly') || L.title;
  L.section = find(l=>l.type==='secHead', byName(/section/i)) || L.title;
  L.quote   = find(byName(/quote/i));
  L.end     = find(byName(/thank|closing|end/i)) || L.section;
  L.parts   = (cfg.partLayouts||[]).map(n=>layouts.find(l=>l.name.trim().toLowerCase()===n.toLowerCase())).filter(Boolean);

  // Where content goes: the template's setting, else the master's body box, else safe margins
  const mb = (masterPh.find(p=>p.type==='body') || {}).box;
  const area = cfg.area || (mb ? { x:mb.x, y:mb.y, w:mb.w, h:Math.min(mb.h, H-mb.y-0.6) } : { x:0.6, y:1.6, w:W-1.2, h:H-2.3 });
  // A placeholder's box, inherited from the master when the layout leaves it out
  const boxOf = (layout, p) => p.box || ((masterPh.find(m=>m.type===p.type) || masterPh.find(m=>m.idx!=null && m.idx===p.idx) || {}).box) || null;
  return { files, layouts, L, area, W, H, boxOf, notesMaster: notesRel ? resolve('ppt/presentation.xml', notesRel.target) : null,
    bodyFont: cfg.bodyFont || '+mn-lt', headFont: cfg.headFont || '+mj-lt', badge: cfg.badge, titleInfo: cfg.titleInfo || null,
    titleFont: cfg.titleFont || '', confidential: cfg.confidential || null, footer: cfg.footer!==false, partColors: cfg.partColors || ['accent1','accent2','accent4','accent3','accent6','tx2'] };
}

/* ===== Drawing ===== */
// Colors are theme colors, so another template recolors the deck: "accent2", "accent2:tint", "accent2:dark", "tx1", "bg1"
function clr(c){
  const [v, mod] = String(c).split(':');
  const m = mod==='tint' ? '<a:lumMod val="20000"/><a:lumOff val="80000"/>' : mod==='soft' ? '<a:lumMod val="40000"/><a:lumOff val="60000"/>' :
            mod==='dark' ? '<a:lumMod val="75000"/>' : mod==='line' ? '<a:lumMod val="85000"/>' : mod==='muted' ? '<a:lumMod val="65000"/><a:lumOff val="35000"/>' : '';
  return `<a:schemeClr val="${v}">${m}</a:schemeClr>`;
}
// plain: text in a template placeholder keeps the template's own font and size unless a run sets them
function rpr(r, fonts, plain){
  const font = r.font==='head' ? fonts.head : r.font==='head-template' ? '+mj-lt' : r.font==='body' || (!r.font && !plain) ? fonts.body : r.font;
  const sz = r.sz || (plain ? 0 : 14);
  return `<a:rPr lang="en-US"${sz?` sz="${Math.round(sz*100)}"`:''}${r.b?' b="1"':''}${r.i?' i="1"':''} dirty="0">${r.color?`<a:solidFill>${clr(r.color)}</a:solidFill>`:''}${font?`<a:latin typeface="${esc(font)}"/><a:cs typeface="${esc(font)}"/>`:''}</a:rPr>`;
}
// paragraph: { runs:[{t,b,i,sz,color,font}], bullet, align, after, before }
function paraXML(p, fonts, plain){
  if(plain){
    const runs = (p.runs||[]).filter(r=>r.t!=='' && r.t!=null).map(r=>`<a:r>${rpr(r,fonts,true)}<a:t>${esc(r.t)}</a:t></a:r>`).join('');
    return `<a:p>${p.align?`<a:pPr algn="${p.align}"/>`:''}${runs}</a:p>`;
  }
  const pp = `<a:pPr${p.bullet?' marL="228600" indent="-228600"':' marL="0" indent="0"'}${p.align?` algn="${p.align}"`:''}>`+
    (p.line?`<a:lnSpc><a:spcPct val="${p.line}"/></a:lnSpc>`:'')+
    `<a:spcBef><a:spcPts val="${Math.round((p.before||0)*100)}"/></a:spcBef><a:spcAft><a:spcPts val="${Math.round((p.after||0)*100)}"/></a:spcAft>`+
    (p.bullet?'<a:buFont typeface="Arial"/><a:buChar char="&#8226;"/>':'<a:buNone/>')+'</a:pPr>';
  const runs = (p.runs||[]).filter(r=>r.t!=='' && r.t!=null).map(r=>`<a:r>${rpr(r,fonts)}<a:t>${esc(r.t)}</a:t></a:r>`).join('');
  const last = (p.runs||[])[0] || {};
  return `<a:p>${pp}${runs}<a:endParaRPr lang="en-US" sz="${Math.round((last.sz||14)*100)}" dirty="0"/></a:p>`;
}

class SlideCtx {
  constructor(tpl, layout){ this.tpl=tpl; this.layout=layout; this.id=1; this.shapes=[]; this.notes=''; this.fonts={ body:tpl.bodyFont, head:tpl.headFont }; }
  P(list, plain){ return list.map(p=>paraXML(p, this.fonts, plain)).join(''); }
  ph(type, paras, opts={}){
    const lay = this.layout.ph;
    const p = typeof type==='function' ? lay.find(type) : lay.find(x=>x.type===type);
    if(!p) return null;
    const id=++this.id;
    this.shapes.push(`<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${esc(opts.name||('Placeholder '+id))}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph${p.rawType?` type="${p.rawType}"`:''}${p.idx!=null?` idx="${p.idx}"`:''}/></p:nvPr></p:nvSpPr><p:spPr/>`+
      `<p:txBody><a:bodyPr${opts.anchor?` anchor="${opts.anchor}"`:''}/><a:lstStyle/>${this.P(paras, true)}</p:txBody></p:sp>`);
    return p;
  }
  shape(o){ // {x,y,w,h, geom, adj, fill, line, lineW, paras, inset, anchor, name, shadow}
    const id=++this.id, ins=o.inset||[0.14,0.1,0.14,0.1];
    const geom = `<a:prstGeom prst="${o.geom||'rect'}"><a:avLst>${o.adj!=null?`<a:gd name="adj" fmla="val ${o.adj}"/>`:''}</a:avLst></a:prstGeom>`;
    const fill = o.fill ? `<a:solidFill>${clr(o.fill)}</a:solidFill>` : '<a:noFill/>';
    const ln = o.line ? `<a:ln w="${E(o.lineW||0.014)}"><a:solidFill>${clr(o.line)}</a:solidFill></a:ln>` : '<a:ln><a:noFill/></a:ln>';
    const fx = o.shadow ? '<a:effectLst><a:outerShdw blurRad="76200" dist="19050" dir="5400000" algn="t" rotWithShape="0"><a:prstClr val="black"><a:alpha val="16000"/></a:prstClr></a:outerShdw></a:effectLst>' : '';
    const tx = o.paras ? `<p:txBody><a:bodyPr wrap="square" lIns="${E(ins[0])}" tIns="${E(ins[1])}" rIns="${E(ins[2])}" bIns="${E(ins[3])}" anchor="${o.anchor||'t'}" rtlCol="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>${this.P(o.paras)}</p:txBody>` : '';
    const isText = o.paras && !o.fill && !o.line;
    this.shapes.push(`<p:sp><p:nvSpPr><p:cNvPr id="${id}" name="${esc(o.name||('Shape '+id))}"/><p:cNvSpPr${isText?' txBox="1"':''}/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${E(o.x)}" y="${E(o.y)}"/><a:ext cx="${E(o.w)}" cy="${E(o.h)}"/></a:xfrm>${geom}${fill}${ln}${fx}</p:spPr>${tx}</p:sp>`);
  }
  table(o){ // {x,y,w, cols:[w...], rows:[{cells:[paras[]], fill:[...], h}], name}
    const id=++this.id, cell=(paras, fill)=>`<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>${this.P(paras.length?paras:[{runs:[{t:''}]}])}</a:txBody><a:tcPr marL="${E(0.1)}" marR="${E(0.1)}" marT="${E(0.06)}" marB="${E(0.06)}">`+
      ['lnL','lnR','lnT','lnB'].map(k=>`<a:${k} w="9525"><a:solidFill>${clr('bg1:line')}</a:solidFill></a:${k}>`).join('')+`<a:solidFill>${clr(fill||'bg1')}</a:solidFill></a:tcPr></a:tc>`;
    const H = o.rows.reduce((a,r)=>a+r.h,0);
    this.shapes.push(`<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="${id}" name="${esc(o.name||('Table '+id))}"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>`+
      `<p:xfrm><a:off x="${E(o.x)}" y="${E(o.y)}"/><a:ext cx="${E(o.cols.reduce((a,b)=>a+b,0))}" cy="${E(H)}"/></p:xfrm><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="1"/>`+
      `<a:tblGrid>${o.cols.map(w=>`<a:gridCol w="${E(w)}"/>`).join('')}</a:tblGrid>`+
      o.rows.map(r=>`<a:tr h="${E(r.h)}">${r.cells.map((c,i)=>cell(c, r.fill && r.fill[i])).join('')}</a:tr>`).join('')+
      `</a:tbl></a:graphicData></a:graphic></p:graphicFrame>`);
  }
  xml(){
    return `${XMLH}<p:sld ${NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>${this.shapes.join('')}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>`;
  }
}

/* ===== Text measuring (estimates, kept on the generous side so text stays inside its box) ===== */
const CHAR_EM = 0.5;   // average character width of Calibri-like fonts, in ems, with some slack
function lineCount(text, widthIn, pt){
  const per = Math.max(6, Math.floor(widthIn / (pt/72*CHAR_EM)));
  let n=0;
  String(text).split(/\n/).forEach(par=>{
    let len=0, lines=1;
    par.split(/\s+/).filter(Boolean).forEach(w=>{
      let wl=w.length;
      while(wl>per){ if(len){ lines++; len=0; } wl-=per; lines++; }
      if(len===0) len=wl; else if(len+1+wl<=per) len+=1+wl; else { lines++; len=wl; }
    });
    n+=lines;
  });
  return n;
}
const LH = pt => pt*1.22/72;
const parasHeight = (list, widthIn) => list.reduce((a,p)=>{ const pt=(p.runs[0]&&p.runs[0].sz)||14; const t=p.runs.map(r=>r.t).join(''); return a + lineCount(t, widthIn-(p.bullet?0.25:0), pt)*LH(pt)*((p.line||100000)/100000) + ((p.after||0)+(p.before||0))/72; }, 0);

/* ===== Case data to slide content ===== */
const TONES = ['accent2','accent4','accent3','accent6','accent1'];
const RISK_TONE = { Low:'accent3', Moderate:'accent4', High:'accent1' };
const BODY=14, LABEL=12.5;

const asList = v => Array.isArray(v) ? v.filter(x=>S(x)) : [];
const firstLetter = t => (String(t).match(/[A-Za-z0-9]/)||['•'])[0].toUpperCase();
const quoteIt = s => /^["“]/.test(s) ? s : '“'+s+'”';

// One field as plain text (for table cells, notes and short facts)
function fieldText(f, d){
  const v=d[f.id];
  switch(f.t){
    case 'text': case 'area': return f.quote ? quoteIt(S(v)) : S(v);
    case 'checks': return asList(v).join(', ');
    case 'radio': { const det=S(d[f.id+'__d']); return [v||'', det].filter(Boolean).join(v&&det?'. ':''); }
    case 'radios': return f.p.filter(([k])=>v&&v[k]).map(([k])=>k+': '+v[k]).join('; ');
    case 'parts': return f.p.filter(k=>S((v||{})[k])).map(k=>k+': '+S(v[k])).join('; ');
    case 'table': return (v||[]).filter(r=>r.some(c=>S(c))).map(r=>f.c.map((c,i)=>S(r[i])?c+': '+S(r[i]):'').filter(Boolean).join('; ')).join('\n');
  }
  return '';
}
const filled = (f,d) => (typeof isFilled==='function' ? isFilled(f,d) : !!fieldText(f,d));

// Turn a section's filled fields into blocks
function sectionBlocks(s, d){
  const out=[]; let facts=null;
  const fact = (label, value, tone) => { if(!facts){ facts={type:'facts', items:[]}; out.push(facts); } facts.items.push({label, value, tone}); };
  const endFacts = () => { facts=null; };
  s.fields.forEach(f=>{
    if(!filled(f,d)) return;
    const v=d[f.id];
    switch(f.t){
      case 'text': fact(f.label, S(v)); break;
      case 'radio': case 'radios': {
        const val=fieldText(f,d);
        if(val.length>90){ endFacts(); out.push({type:'text', label:f.label, text:val}); } else fact(f.label, val, f.id in RISK_FIELDS ? RISK_TONE[v] : null);
        break;
      }
      case 'parts': {
        const items=f.p.filter(k=>S((v||{})[k]));
        if(f.inline){ endFacts(); out.push({type:'stats', label:f.label, items:items.map(k=>({value:S(v[k]), label:k}))}); }
        else if(f.long){ endFacts(); out.push({type:'cards', items:items.map(k=>({label:k, text:S(v[k])}))}); }
        else items.forEach(k=>fact(k, S(v[k])));
        break;
      }
      case 'area': endFacts(); out.push({type:'text', label:f.label, text: f.quote ? quoteIt(S(v)) : S(v), feature: f.id==='primaryDx'}); break;
      case 'checks': endFacts();
        if(f.score) out.push({type:'stats', label:f.label, items:[{value:asList(v).length+'/'+f.o.length, label:f.label+' positive', sub:asList(v).join(', ')}]});
        else out.push({type:'chips', label:f.label, items:asList(v)});
        break;
      case 'table': endFacts(); {
        const rows=(v||[]).filter(r=>r.some(c=>S(c))).map(r=>f.c.map((_,i)=>S(r[i])));
        // drop columns nobody filled in
        const keep=f.c.map((_,i)=>rows.some(r=>r[i]));
        out.push({type:'table', label:f.label, cols:f.c.filter((_,i)=>keep[i]), rows:rows.map(r=>r.filter((_,i)=>keep[i]))});
        break;
      }
    }
  });
  // Short consecutive narratives sit side by side
  const merged=[];
  out.forEach(b=>{
    const prev=merged[merged.length-1];
    if(b.type==='text' && !b.feature && b.text.length<420 && prev && prev.type==='cards' && prev.items.length<3 && prev.short) prev.items.push({label:b.label, text:b.text});
    else if(b.type==='text' && !b.feature && b.text.length<420) merged.push({type:'cards', short:true, items:[{label:b.label, text:b.text}]});
    else merged.push(b);
  });
  return merged.map(b=> b.type==='cards' && b.short && b.items.length===1 ? {type:'text', label:b.items[0].label, text:b.items[0].text} : b);
}
const RISK_FIELDS = { suicideRisk:1, violenceRisk:1 };

/* Notes: everything entered for the section, in full */
function sectionNotes(s, d){
  return s.fields.filter(f=>filled(f,d)).map(f=>f.label+': '+fieldText(f,d)).join('\n\n');
}

/* ===== Laying out blocks on slides ===== */
const GAP = 0.2;

function measure(b, w){
  switch(b.type){
    case 'facts': {
      const n=b.items.length, cols = n<=4 ? n : n===5||n===6||n===9 ? 3 : 4;
      const cw=(w-GAP*(cols-1))/cols, rows=[];
      for(let i=0;i<n;i+=cols){ const r=b.items.slice(i,i+cols); rows.push(Math.max(...r.map(it=>0.2+LH(LABEL)+0.04+lineCount(it.value,cw-0.28,BODY)*LH(BODY)))+0.02); }
      return { h: rows.reduce((a,x)=>a+x,0)+GAP*(rows.length-1), cols, cw, rows };
    }
    case 'text': {
      const pt = b.feature ? 18 : BODY;
      return { h: 0.22 + (b.label?LH(LABEL)+0.06:0) + parasHeight(textParas(b.text, pt), w-0.3) + 0.04, pt };
    }
    case 'cards': {
      const n=b.items.length, cw=(w-GAP*(n-1))/n;
      return { h: Math.max(...b.items.map(it=>0.22+LH(LABEL)+0.06+parasHeight(textParas(it.text,BODY), cw-0.3)+0.04)), cw };
    }
    case 'chips': {
      const ph=0.36, gapc=0.1; let x=0, lines=1;
      b.items.forEach(t=>{ const cw=Math.min(w, chipW(t)); if(x>0 && x+cw>w){ lines++; x=0; } x+=cw+gapc; });
      return { h: LH(LABEL)+0.08 + lines*ph + (lines-1)*0.1, ph };
    }
    case 'stats': {
      const n=b.items.length, tw=Math.min(2.7,(w-GAP*(n-1))/n), hasSub=b.items.some(i=>i.sub);
      const subH = hasSub ? Math.max(...b.items.map(i=>i.sub?lineCount(i.sub,tw-0.24,11)*LH(11):0)) : 0;
      return { h: 1.12 + subH, tw };
    }
    case 'table': {
      const cols=colWidths(b, w), head=rowH(b.cols, cols, 12.5, true), rows=b.rows.map(r=>rowH(r, cols, b.pt||13));
      return { h: (b.label?LH(LABEL)+0.08:0) + head + rows.reduce((a,x)=>a+x,0), cols, head, rowsH:rows };
    }
    case 'mse': {
      const cols=[2.55, w-2.55], rows=b.rows.map(r=>Math.max(rowH([r.label],[cols[0]],13,true), cellH(r.paras, cols[1])));
      return { h: rows.reduce((a,x)=>a+x,0), cols, rowsH:rows };
    }
  }
  return { h:0 };
}
const chipW = t => Math.max(0.7, String(t).length*12/72*0.52 + 0.36);
const rowH = (cells, cols, pt, bold) => Math.max(...cells.map((c,i)=>lineCount(c||' ', cols[i]-0.2, pt)*LH(pt)*(bold?1.04:1)))+0.14;
const cellH = (paras, w) => parasHeight(paras, w-0.2)+0.14;
function colWidths(b, w){
  const n=b.cols.length; if(!n) return [];
  // wider columns for longer text, within limits
  const len=b.cols.map((c,i)=>Math.max(c.length, ...b.rows.map(r=>Math.min(160,(r[i]||'').length)))+12);
  const tot=len.reduce((a,x)=>a+x,0);
  let ws=len.map(l=>Math.max(1.4, w*l/tot)); const s=ws.reduce((a,x)=>a+x,0); ws=ws.map(x=>x*w/s);
  return ws;
}
function textParas(text, pt, opt={}){
  const lines=String(text).split(/\n+/).map(s=>s.trim()).filter(Boolean);
  const bullet = lines.length>1 && lines.every(l=>l.length<260);
  return lines.map(l=>({ runs:[{t:l.replace(/^[-•*]\s*/,''), sz:pt, color:opt.color||'tx1', i:opt.i}], bullet, after: bullet?3:6 }));
}

// Split a text block so the first part fits in maxH; returns [head, rest] or null
function splitText(b, w, maxH){
  const sents=[]; String(b.text).split(/\n+/).forEach((par,pi)=>{ (par.match(/[^.!?]+[.!?]+["”’)]*\s*|[^.!?]+$/g)||[par]).forEach((s,si)=>sents.push({s:s.trim(), br: si===0 && pi>0})); });
  if(sents.length<2) return null;
  let best=0;
  for(let k=1;k<sents.length;k++){
    const t=join(sents.slice(0,k));
    if(measure({...b, text:t}, w).h<=maxH) best=k; else break;
  }
  if(!best) return null;
  return [{...b, text:join(sents.slice(0,best))}, {...b, text:join(sents.slice(best)), label: b.label ? b.label+' (cont.)' : b.label}];
  function join(list){ return list.map((x,i)=>(i&&x.br?'\n':i?' ':'')+x.s).join(''); }
}
function splitRows(b, w, maxH, key){
  const m=measure(b,w); let used=(key==='mse'?0:(b.label?LH(LABEL)+0.08:0)+m.head), k=0;
  while(k<b.rows.length && used+m.rowsH[k]<=maxH){ used+=m.rowsH[k]; k++; }
  if(k===0 || k===b.rows.length) return null;
  return [{...b, rows:b.rows.slice(0,k)}, {...b, rows:b.rows.slice(k), label: b.label ? b.label+' (cont.)' : b.label}];
}

/* Draw one block at (x,y) with width w */
function draw(ctx, b, x, y, w, toneIdx, sectionTone){
  const m=measure(b,w), tone = i => sectionTone || TONES[(toneIdx+i)%TONES.length];
  const labelP = (t, c) => ({ runs:[{t, sz:LABEL, b:true, color:c+':dark'}], after:3 });
  switch(b.type){
    case 'facts': {
      let yy=y;
      m.rows.forEach((rh,ri)=>{
        b.items.slice(ri*m.cols, ri*m.cols+m.cols).forEach((it,ci)=>{
          const t = it.tone || tone(ri*m.cols+ci);
          ctx.shape({ x:x+ci*(m.cw+GAP), y:yy, w:m.cw, h:rh, geom:'roundRect', adj:8000, fill:t+':tint', name:it.label,
            paras:[labelP(it.label, t), { runs:[{t:it.value, sz:BODY, color:'tx1'}] }] });
        });
        yy+=rh+GAP;
      });
      break;
    }
    case 'text': {
      const t=b.tone||tone(0), paras=[...(b.label?[labelP(b.label,t)]:[]), ...textParas(b.text, m.pt)];
      ctx.shape({ x, y, w, h:m.h, geom:'roundRect', adj:b.feature?10000:5000, fill:t+':tint', name:b.label||'Text', paras, inset:[0.15,0.11,0.15,0.08] });
      break;
    }
    case 'cards': {
      b.items.forEach((it,i)=>{ const t=it.tone||tone(i);
        ctx.shape({ x:x+i*(m.cw+GAP), y, w:m.cw, h:m.h, geom:'roundRect', adj:6000, fill:t+':tint', name:it.label, inset:[0.15,0.11,0.15,0.08],
          paras:[labelP(it.label,t), ...textParas(it.text, BODY)] }); });
      break;
    }
    case 'chips': {
      const t=b.tone||tone(0);
      ctx.shape({ x, y, w, h:LH(LABEL)+0.04, paras:[{runs:[{t:b.label, sz:LABEL, b:true, color:'tx1'}]}], inset:[0,0,0,0], name:b.label });
      let cx=0, cy=y+LH(LABEL)+0.08;
      b.items.forEach(s=>{ const cw=Math.min(w, chipW(s)); if(cx>0 && cx+cw>w){ cx=0; cy+=m.ph+0.1; }
        ctx.shape({ x:x+cx, y:cy, w:cw, h:m.ph, geom:'roundRect', adj:50000, fill:t+':tint', line:t+':soft', lineW:0.01, anchor:'ctr', inset:[0.1,0.02,0.1,0.02],
          paras:[{runs:[{t:s, sz:12, color:'tx1'}], align:'ctr'}], name:s });
        cx+=cw+0.1; });
      break;
    }
    case 'stats': {
      b.items.forEach((it,i)=>{ const t=it.tone||tone(i);
        const paras=[{runs:[{t:it.value, sz:it.value.length>9?20:28, b:true, color:t+':dark', font:'head'}], align:'ctr', after:2},
                     {runs:[{t:it.label, sz:12, color:'tx1'}], align:'ctr'}];
        if(it.sub) paras.push({runs:[{t:it.sub, sz:11, color:'tx1:muted', i:true}], align:'ctr', before:3});
        ctx.shape({ x:x+i*(m.tw+GAP), y, w:m.tw, h:m.h, geom:'roundRect', adj:9000, fill:t+':tint', anchor:'ctr', paras, name:it.label, inset:[0.12,0.08,0.12,0.08] }); });
      break;
    }
    case 'table': {
      let yy=y; const t=b.tone||tone(0);
      if(b.label){ ctx.shape({ x, y, w, h:LH(LABEL)+0.04, paras:[{runs:[{t:b.label, sz:LABEL, b:true, color:'tx1'}]}], inset:[0,0,0,0], name:b.label }); yy+=LH(LABEL)+0.08; }
      const rows=[{ h:m.head, cells:b.cols.map(c=>[{runs:[{t:c, sz:12.5, b:true, color:'bg1'}]}]), fill:b.cols.map(()=>t+':dark') }];
      b.rows.forEach((r,ri)=>rows.push({ h:m.rowsH[ri], cells:r.map(c=>[{runs:[{t:c||'', sz:b.pt||13, color:'tx1'}]}]), fill:r.map(()=> ri%2 ? t+':tint' : 'bg1') }));
      ctx.table({ x, y:yy, cols:m.cols, rows, name:b.label||'Table' });
      break;
    }
    case 'mse': {
      const rows=b.rows.map((r,ri)=>({ h:m.rowsH[ri], cells:[[{runs:[{t:r.label, sz:13, b:true, color:(r.risk?'accent1':'accent2')+':dark'}]}], r.paras], fill:[(r.risk?'accent1':'accent2')+':tint', 'bg1'] }));
      ctx.table({ x, y, cols:m.cols, rows, name:'Mental status examination' });
      break;
    }
  }
  return m.h;
}

/* ===== Building the deck ===== */
function deidentify(d, mode){
  const raw = S(d.patient), name = raw.split(/\s*[\/|]\s*/)[0].replace(/\s*,?\s*MRN\b.*$/i,'').trim();
  const mrn = (raw.match(/MRN[:#\s]*([\w-]+)/i)||[])[1] || (raw.split(/\s*[\/|]\s*/)[1]||'').trim();
  const ordered = /,/.test(name) ? name.split(/\s*,\s*/).reverse().join(' ') : name;
  const words = ordered.split(/\s+/).filter(w=>/^[A-Za-zÀ-ÿñÑ'.-]+$/.test(w) && !/^(jr|sr|ii|iii|iv|mr|mrs|ms|miss)\.?$/i.test(w));
  const initials = words.map(w=>w[0].toUpperCase()+'.').join('');
  if(mode==='full') return { d, label: name || 'Patient' };
  const label = mode==='alias' ? 'Patient A' : (initials || 'Patient');
  const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const subs = [];
  if(ordered) subs.push(new RegExp(reEsc(ordered).replace(/\s+/g,'\\s+'),'gi'));
  if(name && name!==ordered) subs.push(new RegExp(reEsc(name).replace(/\s+/g,'\\s+'),'gi'));
  words.filter(w=>w.replace(/\./g,'').length>=3).forEach(w=>subs.push(new RegExp('\\b'+reEsc(w)+'\\b','g')));
  if(mrn && mrn.length>=3) subs.push(new RegExp(reEsc(mrn),'g'));
  const scrub = s => { let t=s; subs.forEach(re=>{ t=t.replace(re, label); }); return t.replace(new RegExp('('+reEsc(label)+')(\\s+'+reEsc(label)+')+','g'),'$1'); };
  const walk = v => typeof v==='string' ? scrub(v) : Array.isArray(v) ? v.map(walk) : v && typeof v==='object' ? Object.fromEntries(Object.entries(v).map(([k,x])=>[k,walk(x)])) : v;
  const out = walk(d); out.patient = label;
  return { d: out, label };
}

function mseRows(d, secs){
  return secs.filter(s=>s.group && s.id!=='mse' && s.fields.some(f=>filled(f,d))).map(s=>({
    label: s.title, risk: !!s.risk,
    paras: s.fields.filter(f=>filled(f,d)).map(f=>{
      const t=fieldText(f,d);
      if(f.t==='checks' || f.t==='area') return { runs:[{t, sz:13, color:'tx1'}], after:2 };
      return { runs:[{t:f.label+': ', sz:13, b:true, color:'tx1'},{t, sz:13, color:'tx1'}], after:2 };
    })
  }));
}

const longDate = dt => dt.toLocaleDateString('en-US',{ month:'long', day:'numeric', year:'numeric' });

/* Plan the deck: a list of slides { kind, title, blocks, notes, ... } */
function plan(data, opts){
  const secs = opts.sections || (typeof SECTIONS!=='undefined' ? SECTIONS : []);
  const { d, label } = deidentify(data, opts.patientAs||'initials');
  const incl = id => !opts.include || opts.include.includes(id);
  const byId = Object.fromEntries(secs.map(s=>[s.id,s]));
  const has = s => s && s.fields.some(f=>filled(f,d));
  const mseSecs = secs.filter(s=>s.group);
  // Parts in order; sections not listed in CASE_FORMAT join the part of the section before them
  const placed = new Set(); CASE_FORMAT.forEach(p=>p.sections.forEach(id=>placed.add(id)));
  const parts = CASE_FORMAT.map(p=>({ part:p.part, sections:p.sections.slice() }));
  secs.forEach((s,i)=>{ if(s.id==='enc' || s.group || placed.has(s.id)) return;
    let prev=null; for(let j=i-1;j>=0;j--){ const id=secs[j].group?'mse':secs[j].id; if(placed.has(id)){ prev=id; break; } }
    const pt = parts.find(p=>p.sections.includes(prev)) || parts[parts.length-1];
    pt.sections.splice(prev ? pt.sections.indexOf(prev)+1 : pt.sections.length, 0, s.id); placed.add(s.id); });

  const slides=[], present=[];
  const presenter = S(opts.presenter) || S(d.interviewer);
  parts.forEach(p=>{
    const items = p.sections.filter(id => id==='mse' ? incl('mse') && mseSecs.some(has) : incl(id) && has(byId[id]));
    if(items.length) present.push({ part:p.part, items });
  });

  slides.push({ kind:'title', title: S(opts.title)||'Case presentation', presenter, date: longDate(opts.date||new Date()),
    info: [label, S(d.agesex), S(d.location)].filter(Boolean).join('  ·  '), attending: S(d.attending) });
  if(opts.dividers && present.length>1) slides.push({ kind:'agenda', title:'Outline', items: present.map(p=>p.part) });

  present.forEach((p,pi)=>{
    if(opts.dividers && present.length>1) slides.push({ kind:'section', title:p.part, kicker:'Part '+(pi+1), part:pi });
    const at = slides.length;
    p.items.forEach(id=>{
      if(id==='mse'){
        const rows=mseRows(d, mseSecs);
        const para = S(d.mseNarr) || (typeof draftMSE==='function' ? draftMSE(d) : '');
        if(rows.length) slides.push({ kind:'content', title:'Mental status examination', blocks:[{type:'mse', rows}], notes: para ? 'MSE (one paragraph): '+para : '' });
        else if(para) slides.push({ kind:'content', title:'Mental status examination', blocks:[{type:'text', label:'', text:para}], notes:'' });
        return;
      }
      const s=byId[id];
      if(id==='cc' && S(d.cc) && S(d.cc).length<=260 && opts.quoteLayout){ slides.push({ kind:'quote', title:quoteIt(S(d.cc)), sub:'Chief complaint, in the patient’s own words', notes:'' }); return; }
      slides.push({ kind:'content', title:s.title, blocks:sectionBlocks(s,d), notes:sectionNotes(s,d), risk:!!s.risk });
    });
    slides.slice(at).forEach(x=>{ x.part=pi; });
  });
  slides.push({ kind:'end', title:'Thank you', sub: presenter });
  return { slides, label };
}

/* Lay content slides out, adding "(cont.)" slides when a section runs long */
function paginate(tpl, slides){
  const A=tpl.area, out=[];
  slides.forEach(sl=>{
    if(sl.kind!=='content'){ out.push(sl); return; }
    let queue=sl.blocks.slice(), page={...sl, blocks:[], placed:[]}, y=A.y, first=true, n=0;
    const flush = () => { out.push(page); n++; page={...sl, title: sl.title+' (cont.)', blocks:[], placed:[]}; y=A.y; };
    while(queue.length){
      const b=queue.shift(), room=A.y+A.h-y, h=measure(b,A.w).h;
      if(h<=room){ page.placed.push({b, y}); y+=h+GAP; continue; }
      const sp = b.type==='text' ? splitText(b, A.w, room) : (b.type==='table'||b.type==='mse') ? splitRows(b, A.w, room, b.type) : null;
      if(sp && room>0.9){ page.placed.push({b:sp[0], y}); queue.unshift(sp[1]); flush(); continue; }
      if(page.placed.length){ queue.unshift(b); flush(); continue; }
      // Too big for an empty slide and cannot be split: place it anyway (smaller text for tables)
      if(b.type==='table' && !b.pt){ queue.unshift({...b, pt:11}); continue; }
      page.placed.push({b, y}); y+=h+GAP;
    }
    if(page.placed.length || !n) out.push(page);
    first=false;
  });
  return out;
}

/* Letter widths of title fonts, in thousandths of the font size. Fonts not listed use a wide average. */
const FONT_W = {
  'Arial Black': (()=>{ const w={' ':333,'!':333,'"':500,'#':667,'$':667,'%':1000,'&':889,"'":278,'(':389,')':389,'*':556,'+':667,',':333,'-':333,'.':333,'/':278,':':333,';':333,'?':611,'@':778,'’':278,'‘':278,'“':500,'”':500,'–':500,'—':1000,'·':333,'•':500};
    '0123456789'.split('').forEach(c=>w[c]=667);
    Object.assign(w,{a:667,b:667,c:667,d:667,e:667,f:389,g:667,h:667,i:333,j:333,k:667,l:333,m:1000,n:667,o:667,p:667,q:667,r:444,s:611,t:444,u:667,v:611,w:944,x:667,y:611,z:556,
      A:778,B:778,C:778,D:778,E:722,F:667,G:833,H:833,I:389,J:667,K:833,L:667,M:944,N:833,O:833,P:722,Q:833,R:778,S:722,T:722,U:833,V:778,W:1000,X:778,Y:778,Z:722});
    return w; })()
};
// Width of text in inches at a point size, with 6% to spare
function textW(text, pt, font){
  const t = FONT_W[font]; let u=0;
  for(const ch of String(text)) u += t ? (t[ch] || 700) : 640;
  return u/1000*pt/72*1.06;
}
// Lines a text needs at a width; Infinity when one word is wider than the line
function wrapCount(text, widthIn, pt, font){
  let lines=0;
  for(const par of String(text).split('\n')){
    let line='', n=1;
    for(const w of par.split(/\s+/).filter(Boolean)){
      if(textW(w, pt, font) > widthIn) return Infinity;
      const tryL = line ? line+' '+w : w;
      if(textW(tryL, pt, font) <= widthIn) line=tryL; else { n++; line=w; }
    }
    lines+=n;
  }
  return lines;
}
/* Largest size (in points) at which text fits a placeholder box, from maxPt down to minPt; 0 if it never fits */
function fitSize(text, box, maxPt, minPt, maxLines, font){
  if(!box) return 0;
  const w = box.w-0.3, h = box.h-0.1;          // the placeholder's inner margins, plus a little to spare
  for(let pt=maxPt; pt>=minPt; pt-=1){
    const n = wrapCount(text, w, pt, font);
    if(n<=(maxLines||99) && n*pt*1.0/72 <= h) return pt;
  }
  return 0;
}

function renderSlide(tpl, sl, idx, total){
  const L = tpl.L;
  const partL = sl.part!=null && L.parts.length ? L.parts[sl.part % L.parts.length] : null;
  const layout = sl.kind==='title' ? L.title : sl.kind==='section' ? L.section : sl.kind==='quote' ? (L.quote||L.content) : sl.kind==='end' ? L.end : (partL||L.content);
  const ctx = new SlideCtx(tpl, layout);
  const titleType = layout.ph.find(p=>p.type==='ctrTitle') ? 'ctrTitle' : 'title';
  const titleBox = (()=>{ const p=layout.ph.find(x=>x.type===titleType); return p ? tpl.boxOf(layout,p) : null; })();
  const bodyPh = p => (p.type==='body'||p.type==='obj'||p.type==='subTitle') && !(tpl.badge && String(p.idx)===String(tpl.badge.idx)) && (!p.box || p.box.w>1.2);
  const H = (t, extra) => [{ runs:[{t, ...(extra||{})}] }];
  // Titles keep the template's font; the size is set so the text fits its box. Each step: [largest, smallest, most lines]
  const fit = (t, box, steps) => { for(const [mx,mn,ln] of steps){ const pt=fitSize(t, box, mx, mn, ln, tpl.titleFont); if(pt) return pt; } return steps[steps.length-1][1]; };
  const T = (t, steps) => H(t, { sz: fit(t, titleBox, steps) });
  const phBox = test => { const p=layout.ph.find(test); return p ? tpl.boxOf(layout,p) : null; };
  const B = (test, t, steps) => ctx.ph(test, H(t, { sz: fit(t, phBox(test), steps) }));
  switch(sl.kind){
    case 'title': {
      ctx.ph(titleType, T(sl.title, [[59,30,2],[30,24,3]]));
      B(p=>p.type==='subTitle'||bodyPh(p), [sl.presenter, sl.date].filter(Boolean).join('  ·  '), [[24,12,1]]);
      const tb = tpl.titleInfo || (titleBox ? { x:titleBox.x, y:Math.min(tpl.H-0.9, titleBox.y+titleBox.h+0.05), w:titleBox.w, h:0.9 } : null);
      if(tb) ctx.shape({ ...tb, inset:[0,0,0,0], name:'Patient',
        paras:[ ...(sl.info?[{ runs:[{t:sl.info, sz:18, b:true, color:'tx1'}] }]:[]),
                ...(sl.attending?[{ runs:[{t:'Attending: '+sl.attending, sz:13, color:'tx1'}], before:2 }]:[]) ] });
      const cb = tpl.confidential || { x:0.8, y:tpl.H-0.55, w:8, h:0.3 };
      ctx.shape({ ...cb, inset:[0,0,0,0], name:'Confidential', paras:[{ runs:[{t:'Confidential patient information. For case conference use only.', sz:11, i:true, color:'tx1:muted'}] }] });
      break;
    }
    case 'agenda': {
      ctx.ph(titleType, T(sl.title, [[32,20,1]]));
      badge(ctx, tpl, layout, 'O');
      const A=tpl.area, bh=0.56, gap=0.2, cols=tpl.partColors;
      const top = A.y + Math.max(0,(A.h - sl.items.length*(bh+gap))/2.4);
      sl.items.forEach((t,i)=>{ const c=cols[i%cols.length], y=top+i*(bh+gap), w=Math.min(8.4, A.w-1);
        ctx.shape({ x:A.x+0.2, y, w, h:bh, geom:'roundRect', adj:12000, fill:c, anchor:'ctr', inset:[0.25,0.04,0.8,0.04], name:t, paras:[{runs:[{t, sz:20, color:'bg1'}]}] });
        ctx.shape({ x:A.x+0.2+w-0.66, y:y+0.05, w:0.46, h:0.46, geom:'ellipse', fill:'bg1', line:c, lineW:0.02, anchor:'ctr', inset:[0,0,0,0], name:'Part '+(i+1),
          paras:[{runs:[{t:String(i+1), sz:16, b:true, color:c==='tx2'?'tx1':c+':dark'}], align:'ctr'}] }); });
      break;
    }
    case 'section':
      ctx.ph(titleType, T(sl.title, [[60,32,2],[34,24,3]]));
      B(bodyPh, sl.kicker, [[24,14,1]]);
      break;
    case 'quote': {
      ctx.ph('title', [{ runs:[{t:sl.title, sz:fit(sl.title, titleBox, [[44,18,6]]), i:true}] }]);
      B(bodyPh, sl.sub, [[18,12,1]]);
      break;
    }
    case 'end':
      ctx.ph(titleType, T(sl.title, [[60,28,1]]));
      if(sl.sub) B(bodyPh, sl.sub, [[18,11,2]]);
      break;
    default: {
      ctx.ph(titleType, T(sl.title, [[32,20,1],[22,14,2]]));
      badge(ctx, tpl, layout, firstLetter(sl.title));
      const A=tpl.area;
      sl.placed.forEach(({b,y},i)=>draw(ctx, b, A.x, y, A.w, i, (sl.risk && (b.type==='text'||b.type==='chips')) ? 'accent1' : null));
    }
  }
  if(tpl.footer && (sl.kind==='content' || sl.kind==='agenda')) ctx.ph('ftr', H('Confidential patient information'));
  ctx.notes = sl.kind==='content' ? (sl.title.endsWith('(cont.)') ? '' : sl.notes||'') : '';
  return { xml: ctx.xml(), layout: layout.path, notes: ctx.notes };
}
/* The colored circle beside the title, with the slide's letter on it. The circle is a placeholder of the
   layout, so the slide must include it to show it; the letter is a text box laid over the circle. */
function badge(ctx, tpl, layout, letter){
  const b = tpl.badge; if(!b) return;
  const p = layout.ph.find(x=>String(x.idx)===String(b.idx)); if(!p) return;
  ctx.ph(q=>q===p, [{ runs:[{t:letter}], align:'ctr' }]);
  const box = tpl.boxOf(layout, p); if(!box) return;
  ctx.shape({ ...box, inset:[0,0,0,0], anchor:'ctr', name:'Letter', paras:[{ runs:[{t:letter, sz:b.size||24, color:b.color||'bg1', font:'head-template'}], align:'ctr' }] });
}

function notesXML(text){
  const paras = String(text).split(/\n/).map(l=>`<a:p><a:r><a:rPr lang="en-US" dirty="0"/><a:t>${esc(l)}</a:t></a:r></a:p>`).join('') || '<a:p><a:endParaRPr lang="en-US"/></a:p>';
  return `${XMLH}<p:notes ${NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>`+
    `<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>`+
    `<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>${paras}</p:txBody></p:sp>`+
    `</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>`;
}

function assemble(tpl, rendered, meta){
  const files = new Map(tpl.files);
  const ct = [], rel = [];
  const relTo = (from, to) => { const a=from.split('/'); a.pop(); const b=to.split('/'); let i=0; while(i<a.length && a[i]===b[i]) i++; return '../'.repeat(a.length-i)+b.slice(i).join('/'); };
  rendered.forEach((r,i)=>{
    const n=i+1, sp=`ppt/slides/slide${n}.xml`;
    files.set(sp, enc.encode(r.xml));
    let rels = `<Relationship Id="rId1" Type="${REL}/slideLayout" Target="${relTo(sp, r.layout)}"/>`;
    ct.push(`<Override PartName="/${sp}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`);
    if(meta.notes && tpl.notesMaster && r.notes){
      const np=`ppt/notesSlides/notesSlide${n}.xml`;
      files.set(np, enc.encode(notesXML(r.notes)));
      files.set(relsPath(np), enc.encode(`${XMLH}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${REL}/notesMaster" Target="${relTo(np, tpl.notesMaster)}"/><Relationship Id="rId2" Type="${REL}/slide" Target="../slides/slide${n}.xml"/></Relationships>`));
      rels += `<Relationship Id="rId2" Type="${REL}/notesSlide" Target="../notesSlides/notesSlide${n}.xml"/>`;
      ct.push(`<Override PartName="/${np}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>`);
    }
    files.set(relsPath(sp), enc.encode(`${XMLH}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${rels}</Relationships>`));
    rel.push(`<Relationship Id="rIdCs${n}" Type="${REL}/slide" Target="slides/slide${n}.xml"/>`);
  });
  const T = k => dec.decode(files.get(k));
  let pres = T('ppt/presentation.xml');
  const ids = `<p:sldIdLst>${rendered.map((_,i)=>`<p:sldId id="${256+i}" r:id="rIdCs${i+1}"/>`).join('')}</p:sldIdLst>`;
  pres = pres.replace(/(<p:sldSz\b)/, ids+'$1');
  files.set('ppt/presentation.xml', enc.encode(pres));
  files.set('ppt/_rels/presentation.xml.rels', enc.encode(T('ppt/_rels/presentation.xml.rels').replace('</Relationships>', rel.join('')+'</Relationships>')));
  const now = new Date().toISOString().replace(/\.\d+Z$/,'Z');
  files.set('docProps/core.xml', enc.encode(`${XMLH}<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${esc(meta.title)}</dc:title><dc:creator>${esc(meta.author||'')}</dc:creator><cp:lastModifiedBy>${esc(meta.author||'')}</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">${now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${now}</dcterms:modified></cp:coreProperties>`));
  files.set('docProps/app.xml', enc.encode(`${XMLH}<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office PowerPoint</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>${rendered.length}</Slides></Properties>`));
  // Keep only parts still in use, and list them in [Content_Types].xml
  // Package-level links to parts that are not in the template (labels, custom properties) are dropped
  files.set('_rels/.rels', enc.encode(T('_rels/.rels').replace(/<Relationship\b[^>]*?\/>/g, m=>{ const t=attr(m,'Target'); return !t || attr(m,'TargetMode')==='External' || files.has(t.replace(/^\//,'')) ? m : ''; })));
  const keep = new Set(['[Content_Types].xml']);
  const visit = part => { if(keep.has(part) || !files.has(part)) return; keep.add(part); const rp=relsPath(part); if(files.has(rp)){ keep.add(rp); readRels(files, part).forEach(r=>{ if(!r.external) visit(resolve(part, r.target)); }); } };
  keep.add('_rels/.rels');
  dec.decode(files.get('_rels/.rels')).replace(/<Relationship\b([^>]*?)\/?>/g,(m,a)=>{ const t=attr(a,'Target'); if(t && attr(a,'TargetMode')!=='External') visit(t.replace(/^\//,'')); return m; });
  for(const k of [...files.keys()]) if(!keep.has(k)) files.delete(k);
  let types = T('[Content_Types].xml').replace(/<Override PartName="\/([^"]+)"[^>]*\/>/g, (m,p)=> files.has(p) ? m : '');
  types = types.replace('</Types>', ct.filter(o=>!types.includes(o.match(/PartName="[^"]+"/)[0])).join('')+'</Types>');
  if(!/Extension="rels"/i.test(types)) types = types.replace('</Types>','<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>');
  files.set('[Content_Types].xml', enc.encode(types));
  return zip(files);
}

/* Public: build the .pptx bytes. opts: { template (ArrayBuffer), templateCfg, title, presenter, patientAs, dividers, notes, include, date } */
async function generate(data, opts){
  const tpl = await loadTemplate(opts.template, opts.templateCfg);
  const { slides, label } = plan(data, { ...opts, quoteLayout: !!tpl.L.quote });
  const pages = paginate(tpl, slides);
  const rendered = pages.map((s,i)=>renderSlide(tpl, s, i, pages.length));
  const bytes = assemble(tpl, rendered, { notes: opts.notes!==false, title: (S(opts.title)||'Case presentation')+' – '+label, author: S(opts.presenter) });
  return { bytes, label, count: pages.length };
}

/* Sections that have something to show, for the options sheet */
function availableSections(d, secs){
  secs = secs || SECTIONS;
  const out=[]; let mse=false;
  secs.forEach(s=>{ if(s.id==='enc') return; const on=s.fields.some(f=>filled(f,d));
    if(s.group){ if(!mse && secs.filter(x=>x.group).some(x=>x.fields.some(f=>filled(f,d)))){ out.push({ id:'mse', num:s.num.replace(/[A-Z]$/,''), title:s.group }); mse=true; } return; }
    if(on) out.push({ id:s.id, num:s.num, title:s.title }); });
  return out;
}

return { TEMPLATES, CASE_FORMAT, generate, availableSections, deidentify, _test:{ loadTemplate, plan, paginate, unzip } };
})();
if (typeof module !== 'undefined') module.exports = CaseSlides;
