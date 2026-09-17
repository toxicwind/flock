// === KIMI HAR-EXACT PROBE — IMPOSSIBLE TO FAIL ===
// Intercepts LIVE token from next SPA request, then replays with exact HAR headers
// Run on www.kimi.ai with CORS unblocked

void (() => {
  'use strict';

  // ====== CONFIG: Extracted from your HAR ======
  const HAR_HEADERS = {
    'x-msh-platform': 'web',
    'x-msh-version': '2.0.0',
    'X-Traffic-Id': 'd87br2oh8njkr90jf520',
    'x-msh-device-id': '7675193681363736833',
    'x-msh-session-id': '1731737410842547033',
    'R-Timezone': 'America/Denver',
    'X-Language': 'en-US',
    'Origin': 'https://www.kimi.ai',
    'Referer': 'https://www.kimi.ai/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US',
    'Content-Type': 'application/json',
    'User-Agent': navigator.userAgent
  };

  const ENDPOINTS = [
    {method: 'POST', url: 'https://notilo.kimi.ai/ws/tickets', body: {}},
    {method: 'POST', url: 'https://gator.volces.com/list', body: {}},
    {method: 'GET', url: 'https://kimi.kimi.team/apiv2/metrics', body: null},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.MembershipService/GetCurrentUser', body: {}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.MembershipService/GetSubscriptionStats', body: {}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.GiftcardService/ListGiftcardCodes', body: {}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.GiftcardService/ListGiftcardClaims', body: {}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.MembershipService/EarmarkCredit', body: {amount: 1, currency: 'USD'}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.membership.v2.MembershipService/FinalizeCredit', body: {transaction_id: 'test'}},
    {method: 'POST', url: 'https://kimi.kimi.team/kimi.gateway.promotionalasset.v1.PromotionalAssetService/ListPromotionalAssets', body: {}},
  ];

  // ====== STATE ======
  const STATE = {
    captured: false,
    token: null,
    tokenSource: null,
    results: [],
    errors: []
  };

  const log = (label, msg) => {
    const line = `[${label}] ${typeof msg === 'string' ? msg : JSON.stringify(msg).slice(0, 200)}`;
    STATE.results.push({t: Date.now(), line});
    console.log(`%c[${label}]`, 'color: #0f0', msg);
  };

  const err = (label, msg) => {
    const line = `[ERR:${label}] ${msg}`;
    STATE.errors.push({t: Date.now(), line});
    console.error(`%c[ERR:${label}]`, 'color: #f00', msg);
  };

  // ====== TOKEN CAPTURE: Hook fetch BEFORE anything else ======
  const _fetch = window.fetch;
  window.fetch = async function(...args) {
    try {
      const [url, opts = {}] = args;
      const headers = opts.headers || {};
      const auth = headers.Authorization || headers.authorization || headers['X-Auth-Token'] || headers['x-auth-token'];
      if (auth && !STATE.captured) {
        STATE.token = auth.replace(/^Bearer\s+/i, '');
        STATE.captured = true;
        STATE.tokenSource = 'fetch_hook';
        log('TOKEN_CAPTURED', `From ${url}: ${STATE.token.slice(0, 40)}...`);
        // Don't block the original request
      }
    } catch (e) {
      err('FETCH_HOOK', e.message);
    }
    return _fetch.apply(this, args);
  };

  // ====== TOKEN CAPTURE: Hook XHR ======
  const _xhrSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
    try {
      if (/auth/i.test(header) && value && !STATE.captured) {
        STATE.token = value.replace(/^Bearer\s+/i, '');
        STATE.captured = true;
        STATE.tokenSource = 'xhr_hook';
        log('TOKEN_CAPTURED', `From XHR ${header}: ${STATE.token.slice(0, 40)}...`);
      }
    } catch (e) {
      err('XHR_HOOK', e.message);
    }
    return _xhrSetHeader.call(this, header, value);
  };

  // ====== TOKEN CAPTURE: Scrape localStorage as fallback ======
  try {
    const lsToken = localStorage.getItem('token_access');
    if (lsToken && !STATE.captured) {
      STATE.token = lsToken;
      STATE.captured = true;
      STATE.tokenSource = 'localStorage';
      log('TOKEN_FALLBACK', 'Using localStorage token_access');
    }
  } catch (e) {
    err('LS_READ', e.message);
  }

  // ====== DECODE JWT ======
  const decodeJwt = (token) => {
    try {
      if (!token || typeof token !== 'string') return null;
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const pad = (4 - payload.length % 4) % 4;
      const padded = payload + '=='.slice(0, pad);
      return JSON.parse(atob(padded));
    } catch (e) {
      return null;
    }
  };

  // ====== API CALL WITH HAR-EXACT HEADERS ======
  const kimiCall = async (method, url, body = null) => {
    try {
      if (!STATE.token) {
        err('NO_TOKEN', `Cannot call ${url} — no token captured yet`);
        return {error: 'no_token'};
      }

      const headers = {
        ...HAR_HEADERS,
        'Authorization': `Bearer ${STATE.token}`
      };

      const opts = {method, headers, credentials: 'include'};
      if (body) opts.body = JSON.stringify(body);

      const resp = await fetch(url, opts);
      const text = await resp.text();
      let json = null;
      try { json = JSON.parse(text); } catch {}

      log('API_OK', `${method} ${url.replace(/^https:\/\//, '')} -> ${resp.status} (${text.length}b)`);
      return {status: resp.status, text: text.slice(0, 500), json, ok: resp.ok};
    } catch (e) {
      err('API_FAIL', `${method} ${url}: ${e.message}`);
      return {error: e.message};
    }
  };

  // ====== PROBE ALL ======
  const probeAll = async () => {
    log('PROBE_START', `Token source: ${STATE.tokenSource || 'none yet'}`);

    if (!STATE.token) {
      log('WAITING', 'No token yet. Triggering a page action to force token capture...');
      // Force the SPA to make a request by scrolling or clicking
      try {
        window.scrollTo(0, document.body.scrollHeight);
        // Click on a chat element if present
        const chatBtn = document.querySelector('[class*="chat"], [class*="message"], button');
        if (chatBtn) chatBtn.click();
      } catch (e) {
        err('FORCE_ACTION', e.message);
      }

      // Wait up to 5 seconds for token capture
      for (let i = 0; i < 50 && !STATE.token; i++) {
        await new Promise(r => setTimeout(r, 100));
      }
    }

    if (!STATE.token) {
      err('TOKEN_TIMEOUT', 'No token captured after 5s. Try clicking around the page first, then run __KIMI_PROBE__() again.');
      return STATE;
    }

    // Decode and log token info
    const decoded = decodeJwt(STATE.token);
    if (decoded) {
      log('TOKEN_INFO', {
        sub: decoded.sub,
        exp: decoded.exp,
        expired: decoded.exp < Date.now() / 1000,
        expires_in: Math.round(decoded.exp - Date.now() / 1000),
        membership: decoded.membershp?.level || decoded.membership?.level,
        region: decoded.region
      });
    }

    // Run all probes
    const results = {};
    for (const ep of ENDPOINTS) {
      results[ep.url] = await kimiCall(ep.method, ep.url, ep.body);
      await new Promise(r => setTimeout(r, 400));
    }

    // Summary
    const working = Object.entries(results).filter(([k, v]) => v.status && v.status < 400);
    const failing = Object.entries(results).filter(([k, v]) => v.status && v.status >= 400);
    const errors = Object.entries(results).filter(([k, v]) => v.error);

    console.log('\n%c=== SUMMARY ===', 'color: #0ff; font-size: 14px');
    console.log(`Working (${working.length}):`, working.map(([k, v]) => `${k.replace(/^https:\/\//, '')} (${v.status})`).join(', ') || 'none');
    console.log(`Failing (${failing.length}):`, failing.map(([k, v]) => `${k.replace(/^https:\/\//, '')} (${v.status})`).join(', ') || 'none');
    console.log(`Errors (${errors.length}):`, errors.map(([k, v]) => `${k.replace(/^https:\/\//, '')} (${v.error})`).join(', ') || 'none');

    // Copy to clipboard
    const payload = JSON.stringify({
      url: location.href,
      timestamp: Date.now(),
      tokenSource: STATE.tokenSource,
      tokenPrefix: STATE.token ? STATE.token.slice(0, 30) : null,
      decoded: decoded,
      results
    }, null, 2);

    try {
      await navigator.clipboard.writeText(payload);
      log('CLIPBOARD', 'Full results copied to clipboard');
    } catch (e) {
      log('CLIPBOARD_FAIL', 'Copy manually from console');
      console.log(payload);
    }

    return results;
  };

  // ====== MANUAL TOKEN INPUT ======
  const setToken = (token) => {
    STATE.token = token;
    STATE.captured = true;
    STATE.tokenSource = 'manual';
    log('TOKEN_MANUAL', `Set manually: ${token.slice(0, 40)}...`);
    return decodeJwt(token);
  };

  // ====== EXPOSE GLOBALS ======
  window.__KIMI_PROBE__ = probeAll;
  window.__KIMI_CALL__ = kimiCall;
  window.__KIMI_SET_TOKEN__ = setToken;
  window.__KIMI_DECODE__ = decodeJwt;
  window.__KIMI_STATE__ = STATE;

  // ====== AUTO-RUN ======
  console.log('%c[KIMI HAR PROBE INSTALLED]', 'color: #0f0; font-size: 16px');
  console.log('Hooks active. The next SPA request will capture the live token.');
  console.log('Type __KIMI_PROBE__() to run full probe (auto-captures token first)');
  console.log('Or paste a token: __KIMI_SET_TOKEN__("eyJ...")');
  console.log('Or call single endpoint: __KIMI_CALL__("POST", "https://notilo.kimi.ai/ws/tickets", {})');

  // Auto-run after 2s to give SPA time to make a request
  setTimeout(() => {
    if (STATE.captured) {
      log('AUTO_TRIGGER', 'Token already captured, auto-probing...');
      probeAll();
    } else {
      log('AUTO_WAIT', 'No token yet. Click around the page or type __KIMI_PROBE__()');
    }
  }, 2000);

})();
