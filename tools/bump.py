import sys,re
# usage: bump.py <app> <entry file>   : reads current CACHE, adds one, puts the entry (with ID and VER filled in) on top of CHANGELOG
app=sys.argv[1]; entry=open(sys.argv[2]).read()
sw=open(app+'/sw.js').read(); n=int(re.search(r"PREFIX \+ 'v(\d+)'",sw).group(1)); open(app+'/sw.js','w').write(sw.replace("PREFIX + 'v%d'"%n,"PREFIX + 'v%d'"%(n+1)))
s=open(app+'/index.html').read(); top=int(re.search(r"const CHANGELOG=\[\n    \{id:(\d+)",s).group(1))
entry=entry.replace('ID',str(top+1)).replace('VER','v%d'%(n+1))
s=s.replace("const CHANGELOG=[\n","const CHANGELOG=[\n"+entry,1); open(app+'/index.html','w').write(s); print('v%d id %d'%(n+1,top+1))
