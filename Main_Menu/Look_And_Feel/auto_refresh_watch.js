// =====================================================================
// AUTO REFRESH WATCHER - shared by every screen.
// Asks this screen's own /dev/changed-since endpoint (every 30 seconds)
// whether any CODE file behind the page has moved since the page was
// loaded, and reloads once when one has. Editing code while a browser
// tab sits open should not need a manual Ctrl+F5 to be seen.
//
// Behaviour contract (mirrors watch_for_file_changes.py):
//   - the first call carries no token, so it only establishes the
//     baseline. It can NEVER trigger a reload, or every fresh page
//     would reload itself in a loop the moment it opened;
//   - the server-side toggle (dev_auto_refresh_toggle.json) turns the
//     RELOAD behaviour off - e.g. for phone/tunnel use - without ever
//     touching the trace ledger or the nightly reflection, both of
//     which keep running regardless;
//   - completely silent. No badge, no console noise, nothing visible.
// =====================================================================
(function () {
  'use strict';

  var POLL_MS = 30000;
  var token = '';

  function poll() {
    fetch('/dev/changed-since?token=' + encodeURIComponent(token))
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data) { return; }
        if (data.changed && token) { location.reload(); return; }
        token = data.fingerprint || '';
      })
      .catch(function () { /* a missed poll is fine; try again next tick */ });
  }

  // First poll settles the baseline shortly after load; the rest keep time.
  setTimeout(poll, 2000);
  setInterval(poll, POLL_MS);
})();
