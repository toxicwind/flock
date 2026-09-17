// === KIMI API PROBE — TESTED, LINTED ===
// Run in browser console on www.kimi.ai with CORS unblocked
// Handles: token extraction, expiry check, auto-refresh, multi-endpoint probe

(() => {
  'use strict';

  const VAULT = [];
  const log = (label, data) => {
    VAULT.push({t: Date.now(), label, data: typeof data === 'string' ? data.slice(0, 500) : JSON.stringify(data).slice(0, 500)});
    console.log(`%c[${label}]`, 'color: #0f0', typeof data === 'string' ? data.slice(0, 200) : data);
  };

  // 1. EXTRACT TOKENS
  const accessToken = localStorage.getItem('token_access');
  const refreshToken = localStorage.getItem('token_refresh');
  const volcanoToken = localStorage.getItem('info-token-volcano');
  const userId = localStorage.getItem('id_user_msh');

  if (!accessToken) {
    console.error('No token_access in localStorage. Log in first.');
    return;
  }

  log('TOKENS', {access: accessToken.slice(0, 40) + '...', refresh: refreshToken ? 'yes' : 'no', userId});

  // 2. DECODE JWT (base64url with padding fix)
  const decodeJwt = (token) => {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = payload + '=='.slice(0, (4 - payload.length % 4) % 4);
      return JSON.parse(atob(padded));
    } catch (e) {
      console.error('Decode failed:', e);
      return null;
    }
  };

  const accessPayload = decodeJwt(accessToken);
  const refreshPayload = decodeJwt(refreshToken);

  if (!accessPayload) {
    console.error('Cannot decode access token');
    return;
  }

  log('DECODED_ACCESS', {
    sub: accessPayload.sub,
    exp: accessPayload.exp,
    expired: accessPayload.exp < Date.now() / 1000,
    expires_in: Math.round(accessPayload.exp - Date.now() / 1000),
    membership: accessPayload.membershp?.level || accessPayload.membership?.level,
    region: accessPayload.region
  });

  // 3. REFRESH FUNCTION
  const doRefresh = async () => {
    if (!refreshToken) {
      log('REFRESH', 'No refresh token available');
      return null;
    }

    const refreshEndpoints = [
      'https://kimi.kimi.team/api/auth/refresh',
      'https://kimi.kimi.team/api/token/refresh',
      'https://kimi.kimi.team/api/v1/auth/refresh',
      'https://kimi.kimi.team/apiv2/auth/refresh',
      'https://account.kimi.ai/api/auth/refresh',
    ];

    for (const url of refreshEndpoints) {
      try {
        log('REFRESH_TRY', url);
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${refreshToken}`,
            'x-refresh-token': refreshToken
          },
          body: JSON.stringify({refresh_token: refreshToken, token: refreshToken})
        });
        log('REFRESH_STATUS', `${url} -> ${resp.status}`);
        if (resp.ok) {
          const data = await resp.json();
          if (data.access_token || data.token || data.accessToken) {
            const newToken = data.access_token || data.token || data.accessToken;
            localStorage.setItem('token_access', newToken);
            log('REFRESH_OK', `New token: ${newToken.slice(0, 40)}...`);
            return newToken;
          }
        }
      } catch (e) {
        log('REFRESH_ERR', `${url}: ${e.message}`);
      }
    }
    return null;
  };

  // 4. API CALL FUNCTION
  const kimiCall = async (endpoint, method = 'GET', body = null) => {
    let token = localStorage.getItem('token_access');
    const payload = decodeJwt(token);

    // Auto-refresh if expired
    if (payload && payload.exp < Date.now() / 1000) {
      log('TOKEN_EXPIRED', 'Refreshing...');
      const newToken = await doRefresh();
      if (newToken) token = newToken;
    }

    const url = endpoint.startsWith('http') ? endpoint : `https://kimi.kimi.team${endpoint}`;
    const opts = {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'x-auth-token': token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    };
    if (body) opts.body = JSON.stringify(body);

    try {
      const resp = await fetch(url, opts);
      const text = await resp.text();
      let json = null;
      try { json = JSON.parse(text); } catch {}
      log('API', `${method} ${endpoint} -> ${resp.status} (${text.length} bytes)`);
      return {status: resp.status, text, json, headers: Object.fromEntries(resp.headers)};
    } catch (e) {
      log('API_ERR', `${endpoint}: ${e.message}`);
      return {error: e.message};
    }
  };

  // 5. PROBE ENDPOINTS
  const probeAll = async () => {
    const endpoints = [
      ['GET', '/api/user'],
      ['GET', '/apiv2/user'],
      ['GET', '/api/v1/user'],
      ['GET', '/api/config'],
      ['GET', '/api/v1/config'],
      ['GET', '/api/subscription'],
      ['GET', '/api/billing'],
      ['GET', '/api/keys'],
      ['GET', '/api/chat/history'],
      ['GET', '/apiv2/metrics'],
      ['POST', '/kimi.gateway.membership.v2.MembershipService/GetCurrentUser', {}],
      ['POST', '/kimi.gateway.membership.v2.MembershipService/GetSubscriptionStats', {}],
      ['POST', '/kimi.gateway.membership.v2.GiftcardService/ListGiftcardCodes', {}],
      ['POST', '/kimi.gateway.membership.v2.GiftcardService/ListGiftcardClaims', {}],
      ['POST', '/kimi.gateway.membership.v2.MembershipService/EarmarkCredit', {amount: 1, currency: 'USD'}],
      ['POST', '/kimi.gateway.membership.v2.MembershipService/FinalizeCredit', {transaction_id: 'test'}],
      ['POST', '/kimi.gateway.promotionalasset.v1.PromotionalAssetService/ListPromotionalAssets', {}],
    ];

    const results = {};
    for (const [method, ep, body] of endpoints) {
      results[ep] = await kimiCall(ep, method, body);
      await new Promise(r => setTimeout(r, 300));
    }

    // Summary
    const working = Object.entries(results).filter(([k, v]) => v.status && v.status < 400);
    const failing = Object.entries(results).filter(([k, v]) => v.status && v.status >= 400);
    console.log('\n=== SUMMARY ===');
    console.log('Working:', working.map(([k, v]) => `${k} (${v.status})`).join(', ') || 'none');
    console.log('Failing:', failing.map(([k, v]) => `${k} (${v.status})`).join(', ') || 'none');

    // Copy full results to clipboard
    const payload = JSON.stringify({userId, vault: VAULT, results}, null, 2);
    navigator.clipboard.writeText(payload).then(() => {
      console.log('%c[COPIED]', 'color: #0ff', 'Full results copied to clipboard');
    }).catch(() => {
      console.log(payload);
    });

    return results;
  };

  // 6. EXPOSE GLOBALS
  window.__KIMI_CALL__ = kimiCall;
  window.__KIMI_PROBE__ = probeAll;
  window.__KIMI_REFRESH__ = doRefresh;
  window.__KIMI_DECODE__ = decodeJwt;
  window.__KIMI_VAULT__ = VAULT;

  console.log('%c[KIMI PROBE READY]', 'color: #0f0; font-size: 16px', 'Type __KIMI_PROBE__() to run full probe');
  console.log('Or: __KIMI_CALL__("/api/user").then(r => console.log(r))');

  // Auto-run after 1s
  setTimeout(probeAll, 1000);

  return {ready: true, userId, membership: accessPayload.membershp?.level};
})();
