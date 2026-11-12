const C=require('./load.js')(process.argv[2]);
const d={ agesex:'34 / F', parentsRel:'Separated', ptRel:'Married', family:[
 {name:'Ramon', rel:'Father', age:'62', psych:true, cond:'Alcohol use'},
 {name:'Lourdes', rel:'Mother', age:'58'},
 {name:'Jun', rel:'Brother', age:'38'},
 {name:'Ana', rel:'Sister', age:'30', psych:true, cond:'MDD'},
 {name:'Mark', rel:'Husband', age:'36'},
 {name:'Bea', rel:'Daughter', age:'8'}, {name:'Migo', rel:'Son', age:'5'},
 {name:'Pedro', rel:'Paternal grandfather', status:'Deceased', age:'70', psych:true, cond:'Suicide'},
 {name:'Rosa', rel:'Paternal grandmother', age:'85'},
 {name:'Tito Ben', rel:'Paternal uncle', age:'60'},
 {name:'Lola Inday', rel:'Maternal grandmother', status:'Deceased'},
 {name:'Neighbor', rel:'Household member (not related)'}
]};
const G=C.genogramLayout(d);
console.log('size', G.w.toFixed(2), G.h.toFixed(2), 'nodes', G.nodes.length, 'lines', G.lines.length, 'left', G.left);
G.nodes.forEach(n=>console.log(n.name.padEnd(12), n.sex, n.x.toFixed(2), n.y.toFixed(2), n.dead?'dead':'', n.fill?'fill':'', n.pt?'PT':''));
require('fs').writeFileSync(process.argv[3], C.genogramSVG(G, 60));
