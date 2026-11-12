// Loads the app's shared (non-UI) code into Node for quick checks
const fs=require('fs');
module.exports = function(path){
  const s=fs.readFileSync(path,'utf8');
  const a=s.indexOf('<script>\n')+9, b=s.indexOf('/* ---------- App ---------- */');
  const code=s.slice(a,b).replace(/^if \(typeof module !== 'undefined'\).*$/mg,'');
  const vm=require('vm'); const ctx={console, TextEncoder, TextDecoder, DOMParser:undefined}; vm.createContext(ctx);
  vm.runInContext(code+'\n;this.__ok=1;', ctx);
  for(const k of ['SECTIONS','genogramLayout','genogramSVG','labsDone','labFlag','extText','isFilled','SCHEMAS','DocxGen','draftMSE','caseDifferential','famMembers','LAB_PANELS'])
    ctx[k] = vm.runInContext('typeof '+k+'!=="undefined"?'+k+':undefined', ctx);
  return ctx;
};
