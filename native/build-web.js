/* Copies the website (the repo root) into native/www for the App Store app, and changes index.html so that
   js/native.js starts first: it restores saved records from the app's own storage and checks the subscription,
   then loads the app. The big inline script becomes js/app.js so it can run after native.js.
   Run: node build-web.js   (from native/). Nothing here changes the website itself. */
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..'), out = path.join(__dirname, 'www');
const COPY = ['index.html', 'slides.js', 'pdf.js', 'fonts', 'templates', 'icon-180.png', 'icon-192.png', 'icon-512.png', 'favicon-32.png'];
fs.rmSync(out, { recursive: true, force: true }); fs.mkdirSync(path.join(out, 'js'), { recursive: true });
for (const f of COPY) fs.cpSync(path.join(root, f), path.join(out, f), { recursive: true });
fs.copyFileSync(path.join(__dirname, 'js', 'native.js'), path.join(out, 'js', 'native.js'));
let html = fs.readFileSync(path.join(out, 'index.html'), 'utf8');
const list = [];
html = html.replace(/<script src="([\w.-]+\.js)"><\/script>\s*/g, (m, src) => { list.push(src); return ''; });
let app = null;
html = html.replace(/<script>([\s\S]{100000,}?)<\/script>/, (m, code) => { app = code; return ''; });
if (!list.includes('slides.js') || !app) throw new Error('index.html: app scripts not found');
// The App Store app also runs on iPhone and Mac, so say "this device" instead of "this iPad".
app = app.replace(/\bthis iPad\b/g, 'this device').replace(/\bThis iPad\b/g, 'This device');
fs.writeFileSync(path.join(out, 'js', 'app.js'), app);
list.push('js/app.js');
html = html.replace('<link rel="manifest" href="manifest.webmanifest">', '')
  .replace('</body>', '<script>window.PI_SCRIPTS = ' + JSON.stringify(list) + ';</script>\n<script src="js/native.js"></script>\n</body>');
fs.writeFileSync(path.join(out, 'index.html'), html);
console.log('www ready: ' + list.join(', ') + ' load after js/native.js');
