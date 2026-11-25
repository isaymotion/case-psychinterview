/* App Store version only. Copied into www/ by build-web.js; never on the website.
   1. Keeps a copy of the saved records (keys starting "psyCaseApp.") in the app's own storage (Capacitor Preferences),
      because iOS may clear a web view's storage when space runs low. If the web view's copy is gone, it is restored.
   2. navigator.share / canShare with files go to the native share sheet (Word, PowerPoint, PDF, backup files).
   3. window.PINative.sub: the monthly subscription (StoreKit). Free users may create FREE_LIMIT patients.
   Then it loads the app's own scripts (window.PI_SCRIPTS) in order. */
(function () {
  'use strict';
  var PFX = 'psyCaseApp.', C = window.Capacitor;
  var PRODUCT = 'com.isaymotion.psychinterview.monthly', FREE_LIMIT = 2, USED = 'pinative.freeUsed', SUBKEY = 'pinative.sub';
  function loadApp() {
    var list = (window.PI_SCRIPTS || []).slice();
    (function next() {
      var src = list.shift(); if (!src) return;
      var s = document.createElement('script'); s.src = src; s.async = false;
      s.onload = next; s.onerror = next; document.body.appendChild(s);
    })();
  }
  if (!C || !C.isNativePlatform || !C.isNativePlatform() || !C.registerPlugin) { loadApp(); return; }
  var Prefs = C.registerPlugin('Preferences'), Files = C.registerPlugin('Filesystem'), Share = C.registerPlugin('Share'),
      IAP = C.registerPlugin('NativePurchases');

  /* 1. storage mirror */
  var SP = Storage.prototype, rawSet = SP.setItem, rawDel = SP.removeItem;
  function mine(st, k) { return st === window.localStorage && typeof k === 'string' && k.indexOf(PFX) === 0; }
  SP.setItem = function (k, v) { rawSet.call(this, k, v); if (mine(this, k)) Prefs.set({ key: k, value: String(v) }).catch(function () {}); };
  SP.removeItem = function (k) { rawDel.call(this, k); if (mine(this, k)) Prefs.remove({ key: k }).catch(function () {}); };
  function localKeys() { var a = [], i, k; for (i = 0; i < localStorage.length; i++) { k = localStorage.key(i); if (k && k.indexOf(PFX) === 0) a.push(k); } return a; }
  function restore() {
    var have = localKeys();
    if (have.length) return Promise.all(have.map(function (k) { return Prefs.set({ key: k, value: localStorage.getItem(k) }); }));
    return Prefs.keys().then(function (r) {
      var keys = (r && r.keys || []).filter(function (k) { return k.indexOf(PFX) === 0; });
      return Promise.all(keys.map(function (k) { return Prefs.get({ key: k }).then(function (g) { if (g && g.value != null) rawSet.call(localStorage, k, g.value); }); }));
    });
  }

  /* 2. share sheet */
  function toB64(buf) {
    var bytes = new Uint8Array(buf), out = '', i, step = 0x8000;
    for (i = 0; i < bytes.length; i += step) out += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    return btoa(out);
  }
  navigator.canShare = function (d) { return !!(d && (d.files && d.files.length || d.url || d.text)); };
  navigator.share = function (d) {
    d = d || {};
    var files = Array.prototype.slice.call(d.files || []);
    return Promise.all(files.map(function (f) {
      var safe = String(f.name || 'file').replace(/[\/\\:*?"<>|]+/g, '-');
      return f.arrayBuffer().then(function (b) { return Files.writeFile({ path: safe, data: toB64(b), directory: 'CACHE' }); })
        .then(function (r) { return r.uri; });
    })).then(function (uris) {
      var o = { title: d.title || '' }; if (uris.length) o.files = uris; if (d.url) o.url = d.url; if (d.text) o.text = d.text;
      return Share.share(o);
    }).then(function () {}, function (e) {
      var m = String(e && (e.message || e) || '');
      if (/cancel/i.test(m)) { var err = new Error('Share canceled'); err.name = 'AbortError'; throw err; }
      throw e;
    });
  };

  /* 3. subscription. "active" is refreshed from StoreKit at start, after a purchase or restore, and when the app returns. */
  var state = { active: false, used: 0, price: '', ready: false };
  function save() { rawSet.call(localStorage, SUBKEY, state.active ? '1' : '0'); Prefs.set({ key: SUBKEY, value: state.active ? '1' : '0' }).catch(function () {}); }
  function check() {
    return IAP.getPurchases({ productType: 'subs', onlyCurrentEntitlements: true }).then(function (r) {
      var now = Date.now();
      state.active = (r && r.purchases || []).some(function (p) {
        if (p.productIdentifier !== PRODUCT) return false;
        if (p.isActive === true) return true;
        return p.expirationDate ? new Date(p.expirationDate).getTime() > now : false;
      });
      save(); return state.active;
    }, function () { return state.active; });
  }
  function loadPrice() {
    return IAP.getProduct({ productIdentifier: PRODUCT, productType: 'subs' }).then(function (r) {
      var p = r && (r.product || r); if (p && p.priceString) state.price = p.priceString;
    }, function () {});
  }
  window.PINative = {
    FREE_LIMIT: FREE_LIMIT,
    sub: state,
    canAddPatient: function () { return state.active || state.used < FREE_LIMIT; },
    freeLeft: function () { return Math.max(0, FREE_LIMIT - state.used); },
    countPatient: function () {
      if (state.active) return;
      state.used++; Prefs.set({ key: USED, value: String(state.used) }).catch(function () {});
    },
    buy: function () {
      return IAP.purchaseProduct({ productIdentifier: PRODUCT, productType: 'subs' }).then(check);
    },
    restore: function () { return IAP.restorePurchases().then(check); },
    manage: function () { return IAP.manageSubscriptions(); },
    refresh: check,
    price: loadPrice
  };
  IAP.addListener('transactionUpdated', function () { check(); }).catch(function () {});
  document.addEventListener('visibilitychange', function () { if (!document.hidden) check(); });

  var subReady = Prefs.get({ key: USED }).then(function (g) { state.used = parseInt(g && g.value, 10) || 0; }, function () {})
    .then(function () { return Prefs.get({ key: SUBKEY }); }).then(function (g) { state.active = !!(g && g.value === '1'); }, function () {})
    .then(function () { return Promise.race([check(), new Promise(function (ok) { setTimeout(ok, 2500); })]); })
    .then(function () { state.ready = true; loadPrice(); });
  Promise.all([restore().catch(function () {}), subReady]).then(loadApp, loadApp);
})();
