// Genogram layout checks: node t_geno.js <index.html> <out folder>
// Lays out every family in fixtures/families.json, writes an SVG of each, and checks the structure.
const C=require('./load.js')(process.argv[2]); const fs=require('fs'), path=require('path');
const cases=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/families.json'),'utf8')), out=process.argv[3]||path.join(__dirname,'out');
const errs=[]; const ok=(c,m)=>{ if(!c) errs.push(m); };
const want={ sample:{nodes:6,left:0}, big:{nodes:22,left:0}, old:{nodes:12,left:0}, lone:{nodes:8,left:0}, solo:{nodes:3,left:2} };   // v42 (Genogram 1.7.0): other relatives, household members and pets are drawn in a last row, so big has 22 people and nobody left out
for(const k in cases){
  const G=C.genogramLayout(cases[k], k==='sample'?{title:'Family genogram — Mark (October 2026)'}:{});
  console.log(k.padEnd(7),'size',G.w.toFixed(1),'x',G.h.toFixed(1),'people',G.nodes.length,'pieces',G.prims.length,'not drawn',JSON.stringify(G.left));
  ok(G.nodes.length===want[k].nodes, k+': people '+G.nodes.length); ok(G.left.length===want[k].left, k+': not drawn '+G.left);
  const nums=[]; G.prims.forEach(p=>{ ['x','y','w','h','x1','y1','x2','y2'].forEach(q=>{ if(q in p) nums.push(p[q]); }); (p.pts||[]).forEach(q=>nums.push(q[0],q[1])); });
  ok(nums.every(n=>typeof n==='number' && isFinite(n)), k+': a bad number in the drawing');
  ok(nums.every(n=>n>=-0.01), k+': something is drawn off the picture');
  // no two symbols overlap
  G.nodes.forEach((a,i)=>G.nodes.forEach((b,j)=>{ if(j>i && Math.abs(a.x-b.x)<1.05 && Math.abs(a.y-b.y)<1.05) errs.push(k+': '+a.name+' overlaps '+b.name); }));
  fs.writeFileSync(path.join(out,'geno_'+k+'.svg'), C.genogramSVG(G, 70));
}
// oldest to youngest: siblings and children are ordered by age, months and years mixed
const row=(G,names)=>names.map(n=>G.nodes.find(x=>x.name===n)).map(n=>n.x);
const inc=a=>a.every((v,i)=>!i||v>a[i-1]);
const B=C.genogramLayout(cases.big);
ok(inc(row(B,['Jun','Patient','Ana'])), 'siblings not oldest to youngest'); ok(inc(row(B,['Bea','Migo','Baby'])), 'children not oldest to youngest (8 mo should be last)');
const shuffled=JSON.parse(JSON.stringify(cases.big)); shuffled.family.reverse();
ok(inc(row(C.genogramLayout(shuffled),['Jun','Patient','Ana'])), 'order depends on the list order');
shuffled.genoByAge=false; ok(!inc(row(C.genogramLayout(shuffled),['Jun','Patient','Ana'])), 'switching age order off had no effect');
ok(Math.abs(C.ageYears('1 y 6 mo')-1.5)<1e-9 && Math.abs(C.ageYears('8 mo')-8/12)<1e-9 && C.ageYears('33')===33 && C.ageYears('62 y/o')===62 && C.ageYears('')===null, 'ageYears');
const s=C.famSorted(shuffled).map(m=>m.name); ok(s.indexOf('Pedro')<s.indexOf('Ramon') && s.indexOf('Jun')<s.indexOf('Ana') && s.indexOf('Bea')<s.indexOf('Baby'), 'famSorted '+s);
ok(C.famLinksOf(cases.big).length===5 && C.famLinksOf({family:[{id:'a',name:'A'}],famLinks:[{a:'pt',b:'zz',type:'Close'},{a:'pt',b:'pt',type:'Close'}]}).length===0, 'famLinksOf');
console.log('errors', JSON.stringify(errs));
