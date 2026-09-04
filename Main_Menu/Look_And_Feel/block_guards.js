// ----------------------------------------------------------------------
//  block_guards.js - the page-wide JS error boundary and freshness stamps.
//
//  WHY THIS EXISTS (Phase-1 W3.1)
//      Every screen's own script already catches its fetch failures -
//      this is the LAST line of defence behind them. If some render
//      path throws unexpectedly, one part of a page failing must name
//      itself quietly instead of killing every other part's updates.
//
//  WHAT IT DOES
//      window.INKY_GUARD.boundary(name, fn)
//          Wraps a function so a throw becomes a named, dismissible
//          corner notice - the rest of the page keeps working.
//      window.INKY_GUARD.freshStamp(el)
//          Stamps "updated HH:MM IST" into an element. India has no
//          daylight saving; the offset is fixed, same clock everywhere.
//      An uncaught error anywhere shows at most one notice per 30
//      seconds - a broken page should not spam.
// ----------------------------------------------------------------------
(function () {
  'use strict';

  var lastToastAt = 0;

  function toast(message) {
    var now = Date.now();
    if (now - lastToastAt < 30000) return;   // never spam
    lastToastAt = now;
    var el = document.createElement('div');
    el.className = 'inky-guard-toast';
    el.setAttribute('role', 'status');
    el.style.cssText = 'position:fixed;bottom:14px;right:14px;z-index:9999;' +
      'max-width:320px;padding:10px 14px;font:12px/1.4 sans-serif;' +
      'background:#222;border:1px solid #555;color:#eee;border-radius:6px;';
    el.textContent = message;
    var dismiss = document.createElement('button');
    dismiss.textContent = 'dismiss';
    dismiss.style.cssText = 'margin-left:10px;background:none;border:none;' +
      'color:#7fd;cursor:pointer;text-decoration:underline;font:inherit;';
    dismiss.onclick = function () { el.remove(); };
    el.appendChild(dismiss);
    document.body.appendChild(el);
  }

  function boundary(name, fn) {
    return function () {
      try {
        return fn.apply(this, arguments);
      } catch (err) {
        if (window.console && console.error) console.error('[inky:' + name + ']', err);
        toast('A part of this page failed (' + name +
              '). The rest still works - reload to retry.');
      }
    };
  }

  // IST: fixed +05:30, no daylight saving.
  function freshStamp(el, when) {
    if (!el) return;
    var d = when ? new Date(when) : new Date();
    var hh = String(d.getHours()).padStart(2, '0');
    var mm = String(d.getMinutes()).padStart(2, '0');
    el.textContent = 'updated ' + hh + ':' + mm + ' IST';
  }

  window.addEventListener('error', function (event) {
    toast('Something on this page failed' +
      (event && event.message ? ': ' + event.message : '') +
      '. The rest may still work - reload to retry.');
  });

  window.INKY_GUARD = { boundary: boundary, freshStamp: freshStamp };
})();
