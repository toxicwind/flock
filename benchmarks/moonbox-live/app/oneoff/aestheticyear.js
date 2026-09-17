// ==UserScript==
// @name         IG Mirror – jQuery Edition (Year Overlay + Aesthetic Grid)
// @namespace    https://ig-mirror.local/
// @version      0.13.2
// @description  Side mirror for Instagram tag/search grids using jQuery. Per-tag/search state, route-aware clear & reload, stable ghost, date debugging, hydration via GraphQL, and elegant year overlays.
// @match        https://www.instagram.com/explore/tags/*
// @match        https://www.instagram.com/explore/search/keyword/*
// @grant        GM_addStyle
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @require      https://code.jquery.com/jquery-3.7.1.min.js#sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo=
// @run-at       document-idle
// @connect      www.instagram.com
// @connect      i.instagram.com
// ==/UserScript==

;(function ($) {
  'use strict'

  // Route detection for per-tag/search state
  function routeCtx() {
    const u = new URL(location.href)
    if (u.pathname.startsWith('/explore/tags/')) {
      const parts = u.pathname.split('/').filter(Boolean)
      const tag = (parts[2] || '').toLowerCase()
      return { scope: 'tag', key: `tag:${tag}`, label: `#${tag}` }
    }
    if (u.pathname.startsWith('/explore/search/keyword/')) {
      const q = (u.searchParams.get('q') || '').trim().toLowerCase()
      return {
        scope: 'search',
        key: `search:${q}`,
        label: q ? `search: ${q}` : 'search',
      }
    }
    return {
      scope: 'path',
      key: `path:${u.pathname}${u.search}`,
      label: u.pathname,
    }
  }

  let ROUTE = routeCtx()
  let STORAGE_KEY = 'igmjq_state::' + ROUTE.key

  // Global state
  let SORT_DIR = GM_getValue('igmjq_sort', 'asc')
  let PAUSED = false
  let SHOW_MISSING = true
  let DEBUG_OPEN = false

  // shortcode -> { href, img, img_source, ts, ts_source, ts_raw, live, when }
  const items = new Map()
  const queue = []
  let inflight = 0
  const CONCURRENCY = 2
  let APP_ID = null

  GM_addStyle(`
    #igmjq-panel{position:fixed;top:0;right:0;width:420px;height:100vh;z-index:999999;
      background:rgba(18,18,18,.88);backdrop-filter:blur(10px);color:#f5f5f5;border-left:1px solid #2b2b2b;
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;transform:translateX(0);transition:transform .25s}
    #igmjq-panel[hidden]{transform:translateX(100%)}
    #igmjq-panel .head{display:flex;align-items:center;justify-content:space-between;padding:10px 12px}
    #igmjq-panel .head .title{font-weight:700;letter-spacing:.2px}
    #igmjq-panel .head .subtitle{color:#9aa0a6;font-size:12px;margin-left:6px}
    #igmjq-panel .head .buttons{display:flex;gap:8px;flex-wrap:wrap}
    #igmjq-panel .head .buttons button{all:unset;cursor:pointer;background:#242424;border:1px solid #333;border-radius:10px;padding:6px 10px;color:#d6d6d6}
    #igmjq-panel .head .buttons button:hover{color:#fff;border-color:#444}
    #igmjq-panel .body{height:calc(100% - 56px);overflow:auto;padding:12px}

    #igmjq-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
    #igmjq-grid a{display:block;position:relative;aspect-ratio:1/1;background:linear-gradient(180deg,#2b2b2b,#1d1d1d);border-radius:14px;overflow:hidden;
      box-shadow:0 1px 1px rgba(0,0,0,.25), 0 8px 24px rgba(0,0,0,.35);transition:transform .18s ease, box-shadow .18s ease;will-change:transform}
    #igmjq-grid a:hover{transform:translateY(-2px);box-shadow:0 2px 2px rgba(0,0,0,.25), 0 16px 32px rgba(0,0,0,.45)}
    #igmjq-grid img{width:100%;height:100%;object-fit:cover;display:block}

    .igmjq-scrim{position:absolute;inset:auto 0 0 0;height:36%;background:linear-gradient(180deg,rgba(0,0,0,0) 0%, rgba(0,0,0,.28) 46%, rgba(0,0,0,.55) 100%)}
    .igmjq-badge{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.55);color:#fff;font-size:10px;padding:3px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.1)}

    .igmjq-year{position:absolute;left:8px;bottom:8px;display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:12px;letter-spacing:.3px;
      padding:4px 9px;border-radius:999px;color:#fff;border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(6px)}
    .igmjq-year.age-0{background:rgba(0,0,0,.38)}
    .igmjq-year.age-3{background:linear-gradient(90deg,#3a3a3a,#2a2a2a)}
    .igmjq-year.age-6{background:linear-gradient(90deg,#6b4f1d,#3a2d12)}
    .igmjq-year.age-10{background:linear-gradient(90deg,#7a1f1f,#3a1111)}
    .igmjq-year .dot{width:6px;height:6px;border-radius:999px;background:#a3a3a3}
    .igmjq-year.age-3 .dot{background:#d0a85c}
    .igmjq-year.age-6 .dot{background:#f39c12}
    .igmjq-year.age-10 .dot{background:#ff5b5b}

    #igmjq-debug{margin-top:12px;background:#141414;border:1px solid #2a2a2a;border-radius:12px;padding:8px;max-height:45vh;overflow:auto}
    #igmjq-debug table{width:100%;border-collapse:collapse;font-size:12px;color:#ddd}
    #igmjq-debug th,#igmjq-debug td{border-bottom:1px solid #242424;padding:6px 4px;text-align:left}
    #igmjq-debug .warn{color:#ffbd4a}
  `)

  const $panel = $(`
    <aside id="igmjq-panel">
      <div class="head">
        <div>
          <span class="title">IG Mirror</span>
          <span class="subtitle" id="igmjq-scope"></span>
          <span id="igmjq-count" style="color:#aaa;font-weight:400;margin-left:6px">0</span>
        </div>
        <div class="buttons">
          <button id="igmjq-sort">Sort: <b>${SORT_DIR}</b></button>
          <button id="igmjq-toggle">${PAUSED ? 'Play' : 'Pause'}</button>
          <button id="igmjq-missing">${SHOW_MISSING ? 'Hide missing' : 'Show missing'}</button>
          <button id="igmjq-debug-btn">${DEBUG_OPEN ? 'Close debug' : 'Debug'}</button>
          <button id="igmjq-clear">Clear</button>
        </div>
      </div>
      <div class="body">
        <div id="igmjq-grid"></div>
        <div id="igmjq-debug" ${DEBUG_OPEN ? '' : 'hidden'}></div>
      </div>
    </aside>
  `).appendTo(document.body)

  function updateScopeLabel() {
    $('#igmjq-scope').text(`(${ROUTE.label})`)
  }
  updateScopeLabel()

  // Alt+I toggles panel
  $(document).on('keydown', e => {
    if (e.altKey && String(e.key).toLowerCase() === 'i') {
      e.preventDefault()
      $panel.prop('hidden', !$panel.prop('hidden'))
    }
  })

  $('#igmjq-sort').on('click', () => {
    SORT_DIR = SORT_DIR === 'asc' ? 'desc' : 'asc'
    GM_setValue('igmjq_sort', SORT_DIR)
    $('#igmjq-sort b').text(SORT_DIR)
    render()
  })
  $('#igmjq-toggle').on('click', () => {
    PAUSED = !PAUSED
    $('#igmjq-toggle').text(PAUSED ? 'Play' : 'Pause')
  })
  $('#igmjq-missing').on('click', () => {
    SHOW_MISSING = !SHOW_MISSING
    $('#igmjq-missing').text(SHOW_MISSING ? 'Hide missing' : 'Show missing')
    render()
  })
  $('#igmjq-debug-btn').on('click', () => {
    DEBUG_OPEN = !DEBUG_OPEN
    $('#igmjq-debug-btn').text(DEBUG_OPEN ? 'Close debug' : 'Debug')
    $('#igmjq-debug').prop('hidden', !DEBUG_OPEN)
    if (DEBUG_OPEN) renderDebug()
  })
  $('#igmjq-clear').on('click', () => {
    if (confirm(`Clear mirrored items for ${ROUTE.label}?`)) {
      items.clear()
      GM_setValue(STORAGE_KEY, null)
      render()
      renderDebug()
    }
  })

  const dedupe = arr => [...new Set(arr)]
  const getShortcode = href => {
    try {
      const u = new URL(href, location.origin)
      const m = u.pathname.match(/^\/(?:p|reel)\/([^\/]+)/)
      return m ? m[1] : null
    } catch {
      return null
    }
  }
  const bestFromResources = res => {
    if (!res) return null
    if (Array.isArray(res))
      return res[res.length - 1]?.src || res[res.length - 1]?.url || null
    if (res.candidates) return res.candidates[0]?.url || null
    return null
  }
  const persist = () => {
    const dump = JSON.stringify([...items.entries()])
    GM_setValue(STORAGE_KEY, dump)
  }
  const restore = () => {
    try {
      const dump = GM_getValue(STORAGE_KEY)
      if (!dump) return
      const ent = JSON.parse(dump)
      for (const [k, v] of ent) items.set(k, v)
    } catch {}
  }
  const toIso = ms => (Number.isFinite(ms) ? new Date(ms).toISOString() : '')

  function findAppId() {
    if (APP_ID) return APP_ID
    $('script[type="application/json"]').each(function () {
      const txt = this.textContent || ''
      const m = txt.match(/"APP_ID":"(\d+)"/)
      if (m) {
        APP_ID = m[1]
        return false
      }
    })
    return APP_ID
  }

  // Year styling buckets
  const nowYear = new Date().getFullYear()
  function yearBucket(y) {
    if (!y) return 'age-0'
    const d = nowYear - y
    if (d >= 10) return 'age-10'
    if (d >= 6) return 'age-6'
    if (d >= 3) return 'age-3'
    return 'age-0'
  }

  // GraphQL hydration endpoints
  function gqlShortcodeHash(shortcode) {
    console.log(
      `[IGM][DEBUG] Starting gqlShortcodeHash for shortcode: ${shortcode}`
    )
    const url = `https://www.instagram.com/graphql/query/?query_hash=2c4c2e343a8f64c625ba02b2aa12c7f8&variables=${encodeURIComponent(JSON.stringify({ shortcode }))}`
    console.log(`[IGM][DEBUG] Hash URL: ${url}`)

    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url,
        onload: r => {
          console.log(
            `[IGM][DEBUG] Hash response status: ${r.status}, statusText: ${r.statusText}`
          )
          console.log(
            `[IGM][DEBUG] Hash response text: ${r.responseText.substring(0, 500)}...`
          )

          try {
            const obj = JSON.parse(r.responseText)
            console.log(`[IGM][DEBUG] Hash parsed object:`, obj)

            const node = obj?.data?.shortcode_media
            console.log(`[IGM][DEBUG] Hash shortcode_media node:`, node)

            if (node) {
              const tsRaw =
                typeof node.taken_at_timestamp === 'number'
                  ? node.taken_at_timestamp
                  : null
              console.log(
                `[IGM][DEBUG] Hash taken_at_timestamp: ${node.taken_at_timestamp}, tsRaw: ${tsRaw}`
              )

              const result = {
                ts: Number.isFinite(tsRaw) ? tsRaw * 1000 : Number.NaN,
                ts_source:
                  tsRaw != null ? 'hash.taken_at_timestamp' : 'hash.none',
                ts_raw: tsRaw,
                img:
                  bestFromResources(node.display_resources) ||
                  node.display_url ||
                  null,
                img_source: node.display_resources
                  ? 'hash.display_resources'
                  : node.display_url
                    ? 'hash.display_url'
                    : 'hash.none',
              }
              console.log(`[IGM][DEBUG] Hash result:`, result)
              resolve(result)
            } else if (obj?.status === 'fail') {
              console.log(
                `[IGM][DEBUG] Hash API failure: ${obj.message || 'fail'}`
              )
              reject(new Error(obj.message || 'fail'))
            } else {
              console.log(`[IGM][DEBUG] Hash no data found`)
              reject(new Error('no_data'))
            }
          } catch (e) {
            console.log(`[IGM][DEBUG] Hash JSON parse error:`, e)
            reject(e)
          }
        },
        onerror: e => {
          console.log(`[IGM][DEBUG] Hash request error:`, e)
          reject(e)
        },
      })
    })
  }

  function gqlShortcodeQueryId(shortcode) {
    console.log(
      `[IGM][DEBUG] Starting gqlShortcodeQueryId for shortcode: ${shortcode}`
    )
    const url = `https://www.instagram.com/graphql/query/?query_id=9496392173716084&variables=${encodeURIComponent(JSON.stringify({ shortcode, __relay_internal__pv__PolarisFeedShareMenurelayprovider: true, __relay_internal__pv__PolarisIsLoggedInrelayprovider: true }))}`
    console.log(`[IGM][DEBUG] QueryId URL: ${url}`)

    const headers = {}
    const app = findAppId()
    if (app) {
      headers['X-IG-App-ID'] = app
      console.log(`[IGM][DEBUG] Using App-ID: ${app}`)
    } else {
      console.log(`[IGM][DEBUG] No App-ID found`)
    }

    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url,
        headers,
        onload: r => {
          console.log(
            `[IGM][DEBUG] QueryId response status: ${r.status}, statusText: ${r.statusText}`
          )
          console.log(
            `[IGM][DEBUG] QueryId response text: ${r.responseText.substring(0, 500)}...`
          )

          try {
            const obj = JSON.parse(r.responseText)
            console.log(`[IGM][DEBUG] QueryId parsed object:`, obj)

            const node =
              obj?.data?.xdt_api__v1__media__shortcode__web_info?.items?.[0]
            console.log(`[IGM][DEBUG] QueryId node:`, node)

            if (node) {
              const tsPicked =
                typeof node.taken_at === 'number'
                  ? node.taken_at
                  : typeof node.taken_at_timestamp === 'number'
                    ? node.taken_at_timestamp
                    : null
              const tsSource =
                typeof node.taken_at === 'number'
                  ? 'id.taken_at'
                  : typeof node.taken_at_timestamp === 'number'
                    ? 'id.taken_at_timestamp'
                    : 'id.none'
              console.log(
                `[IGM][DEBUG] QueryId taken_at: ${node.taken_at}, taken_at_timestamp: ${node.taken_at_timestamp}`
              )
              console.log(
                `[IGM][DEBUG] QueryId tsPicked: ${tsPicked}, tsSource: ${tsSource}`
              )

              let imgUrl = null,
                imgSrc = 'id.none'
              if (node.image_versions2?.candidates) {
                imgUrl = bestFromResources(node.image_versions2.candidates)
                imgSrc = 'id.image_versions2'
              } else if (node.display_resources) {
                imgUrl = bestFromResources(node.display_resources)
                imgSrc = 'id.display_resources'
              }

              const result = {
                ts: Number.isFinite(tsPicked) ? tsPicked * 1000 : Number.NaN,
                ts_source: tsSource,
                ts_raw: tsPicked,
                img: imgUrl || null,
                img_source: imgSrc,
              }
              console.log(`[IGM][DEBUG] QueryId result:`, result)
              resolve(result)
            } else {
              console.log(`[IGM][DEBUG] QueryId no items found`)
              reject(new Error('no_items'))
            }
          } catch (e) {
            console.log(`[IGM][DEBUG] QueryId JSON parse error:`, e)
            reject(e)
          }
        },
        onerror: e => {
          console.log(`[IGM][DEBUG] QueryId request error:`, e)
          reject(e)
        },
      })
    })
  }

  function pump() {
    if (PAUSED) return
    while (inflight < CONCURRENCY && queue.length) {
      const sc = queue.shift()
      console.log(
        `[IGM][DEBUG] Starting hydration for shortcode: ${sc}, inflight: ${inflight}`
      )
      inflight++
      hydrate(sc).finally(() => {
        inflight--
        console.log(
          `[IGM][DEBUG] Completed hydration for shortcode: ${sc}, inflight now: ${inflight}`
        )
        render()
        if (DEBUG_OPEN) renderDebug()
        pump()
      })
    }
  }

  async function hydrate(shortcode) {
    console.log(`[IGM][DEBUG] Hydrating shortcode: ${shortcode}`)
    const rec = items.get(shortcode)
    if (!rec) {
      console.log(`[IGM][DEBUG] No record found for shortcode: ${shortcode}`)
      return
    }
    if (Number.isFinite(rec.ts) && rec.img) {
      console.log(
        `[IGM][DEBUG] Shortcode ${shortcode} already has ts: ${rec.ts} and img: ${rec.img ? 'yes' : 'no'}`
      )
      return
    }

    console.log(
      `[IGM][DEBUG] Shortcode ${shortcode} needs hydration - ts: ${rec.ts}, img: ${rec.img ? 'yes' : 'no'}`
    )

    try {
      console.log(`[IGM][DEBUG] Trying QueryId for ${shortcode}`)
      const b = await gqlShortcodeQueryId(shortcode)
      console.log(`[IGM][DEBUG] QueryId success for ${shortcode}:`, b)
      merge(shortcode, b)

      if (!items.get(shortcode).img) {
        console.log(
          `[IGM][DEBUG] Still no img for ${shortcode}, trying Hash fallback`
        )
        try {
          merge(shortcode, await gqlShortcodeHash(shortcode))
        } catch (e) {
          console.log(`[IGM][DEBUG] Hash fallback failed for ${shortcode}:`, e)
        }
      }
    } catch (e) {
      console.log(
        `[IGM][DEBUG] QueryId failed for ${shortcode}, trying Hash:`,
        e
      )
      try {
        merge(shortcode, await gqlShortcodeHash(shortcode))
      } catch (e2) {
        console.log(
          `[IGM][DEBUG] Both APIs failed for ${shortcode}. QueryId:`,
          e,
          'Hash:',
          e2
        )
      }
    }
  }

  function merge(shortcode, data) {
    console.log(`[IGM][DEBUG] Merging data for ${shortcode}:`, data)
    const rec = items.get(shortcode)
    if (!rec) {
      console.log(`[IGM][DEBUG] No record to merge for ${shortcode}`)
      return
    }

    if (data.img && !rec.img) {
      console.log(`[IGM][DEBUG] Setting img for ${shortcode}: ${data.img}`)
      rec.img = data.img
      rec.img_source = data.img_source || rec.img_source || 'unknown'
    }

    if (Number.isFinite(data.ts) && !Number.isFinite(rec.ts)) {
      console.log(
        `[IGM][DEBUG] Setting ts for ${shortcode}: ${data.ts} (source: ${data.ts_source})`
      )
      rec.ts = data.ts
      rec.ts_source = data.ts_source || 'unknown'
      rec.ts_raw =
        typeof data.ts_raw !== 'undefined'
          ? data.ts_raw
          : Number.isFinite(data.ts)
            ? Math.round(data.ts / 1000)
            : null
    }

    if (!Number.isFinite(rec.ts)) {
      rec.ts_source = rec.ts_source || 'none'
      if (typeof rec.ts_raw === 'undefined') rec.ts_raw = null
      console.warn('[IGM][undated]', shortcode, {
        source: rec.ts_source,
        raw: rec.ts_raw,
      })
    }

    console.log(`[IGM][DEBUG] Final record for ${shortcode}:`, rec)
    persist()
  }

  function findDomTimeForShortcode(sc) {
    console.log(`[IGM][DEBUG] Looking for DOM time for shortcode: ${sc}`)
    try {
      const $a = $(`a[href*="/${sc}"]`).first()
      console.log(`[IGM][DEBUG] Found ${$a.length} anchor(s) for ${sc}`)

      if (!$a.length) return null

      const $article = $a.closest('article')
      const $div = $a.closest('div')
      console.log(
        `[IGM][DEBUG] Closest article: ${$article.length}, closest div: ${$div.length}`
      )

      const $time = $a.closest('article,div').find('time[datetime]').first()
      console.log(
        `[IGM][DEBUG] Found ${$time.length} time element(s) with datetime`
      )

      if ($time.length) {
        const iso = $time.attr('datetime')
        console.log(`[IGM][DEBUG] Datetime attribute: ${iso}`)

        const ms = Date.parse(iso)
        console.log(
          `[IGM][DEBUG] Parsed date: ${ms}, isFinite: ${Number.isFinite(ms)}`
        )

        if (Number.isFinite(ms)) {
          const result = { ms, iso, source: 'dom.time' }
          console.log(`[IGM][DEBUG] DOM time result for ${sc}:`, result)
          return result
        }
      } else {
        // Let's also try looking for time elements without datetime
        const $timeAll = $a.closest('article,div').find('time')
        console.log(
          `[IGM][DEBUG] Found ${$timeAll.length} time element(s) total`
        )
        $timeAll.each((i, el) => {
          console.log(`[IGM][DEBUG] Time element ${i}:`, {
            datetime: el.getAttribute('datetime'),
            title: el.getAttribute('title'),
            textContent: el.textContent,
            innerHTML: el.innerHTML,
          })
        })

        // Also try looking for any elements with date-like attributes
        const $dateElements = $a
          .closest('article,div')
          .find('[data-timestamp], [data-time], [title*="202"], [title*="201"]')
        console.log(
          `[IGM][DEBUG] Found ${$dateElements.length} potential date elements`
        )
        $dateElements.each((i, el) => {
          console.log(`[IGM][DEBUG] Date element ${i}:`, {
            tagName: el.tagName,
            dataTimestamp: el.getAttribute('data-timestamp'),
            dataTime: el.getAttribute('data-time'),
            title: el.getAttribute('title'),
            textContent: el.textContent?.substring(0, 100),
          })
        })
      }
    } catch (e) {
      console.log(`[IGM][DEBUG] Error in findDomTimeForShortcode for ${sc}:`, e)
    }
    return null
  }

  function scanOnce() {
    if (PAUSED) return
    console.log(`[IGM][DEBUG] Starting scanOnce`)

    const anchors = $('a[href^="/p/"], a[href^="/reel/"]')
      .map((_, a) => a.href)
      .get()
    console.log(
      `[IGM][DEBUG] Found ${anchors.length} Instagram post/reel anchors`
    )

    const currentShortcodes = new Set()

    // Process currently visible items
    for (const href of dedupe(anchors)) {
      const sc = getShortcode(href)
      if (!sc) {
        console.log(
          `[IGM][DEBUG] Could not extract shortcode from href: ${href}`
        )
        continue
      }
      currentShortcodes.add(sc)

      let rec = items.get(sc)
      if (!rec) {
        console.log(`[IGM][DEBUG] New shortcode found: ${sc}`)
        // New item - add it
        rec = {
          href,
          img: null,
          img_source: null,
          ts: Number.NaN,
          ts_source: null,
          ts_raw: null,
          live: true,
          when: Date.now(),
        }
        items.set(sc, rec)

        const $img = $(`a[href*="${sc}"]`).find('img').first()
        console.log(
          `[IGM][DEBUG] Found ${$img.length} img element(s) for ${sc}`
        )

        const srcset = $img.attr('srcset')
        const src = $img.attr('src')
        console.log(
          `[IGM][DEBUG] Img srcset: ${srcset ? 'present' : 'none'}, src: ${src ? 'present' : 'none'}`
        )

        if (srcset) {
          const best = srcset
            .split(',')
            .map(s => s.trim().split(' ')[0])
            .pop()
          if (best) {
            rec.img = best
            rec.img_source = 'dom.srcset'
            console.log(`[IGM][DEBUG] Set img from srcset for ${sc}: ${best}`)
          }
        } else if (src) {
          rec.img = src
          rec.img_source = 'dom.src'
          console.log(`[IGM][DEBUG] Set img from src for ${sc}: ${src}`)
        }

        const dt = findDomTimeForShortcode(sc)
        if (dt) {
          rec.ts = dt.ms
          rec.ts_source = dt.source
          rec.ts_raw = Math.round(dt.ms / 1000)
          console.log(
            `[IGM][DEBUG] Set DOM time for ${sc}: ${dt.ms} (${dt.iso})`
          )
        } else {
          console.log(`[IGM][DEBUG] No DOM time found for ${sc}`)
        }

        queue.push(sc)
        console.log(`[IGM][DEBUG] Added ${sc} to hydration queue`)
      } else {
        // Existing item - update metadata only, mark as live
        rec.href = href
        rec.live = true
        if (!rec.img) {
          const $img = $(`a[href*="${sc}"]`).find('img').first()
          const srcset = $img.attr('srcset')
          const src = $img.attr('src')
          if (srcset) {
            const best = srcset
              .split(',')
              .map(s => s.trim().split(' ')[0])
              .pop()
            if (best) {
              rec.img = best
              rec.img_source = rec.img_source || 'dom.srcset'
            }
          } else if (src) {
            rec.img = src
            rec.img_source = rec.img_source || 'dom.src'
          }
        }
        if (!Number.isFinite(rec.ts)) {
          const dt2 = findDomTimeForShortcode(sc)
          if (dt2) {
            rec.ts = dt2.ms
            rec.ts_source = dt2.source
            rec.ts_raw = Math.round(dt2.ms / 1000)
          }
        }
      }
    }

    // Mark items not currently visible as ghosts
    for (const [sc, rec] of items) {
      if (!currentShortcodes.has(sc)) {
        rec.live = false // ghost
      }
    }

    persist()
    render()
    if (DEBUG_OPEN) renderDebug()
    pump()
  }

  const debouncedScan = debounce(scanOnce, 300)
  function debounce(fn, ms) {
    let t
    return () => {
      clearTimeout(t)
      t = setTimeout(fn, ms)
    }
  }

  const mo = new MutationObserver(muts => {
    if (PAUSED) return
    for (const m of muts) {
      if (
        m.type === 'childList' &&
        (m.addedNodes?.length || m.removedNodes?.length)
      ) {
        debouncedScan()
        return
      }
      if (m.type === 'attributes') {
        debouncedScan()
        return
      }
    }
  })

  function render() {
    let arr = [...items.values()]
    if (!SHOW_MISSING) arr = arr.filter(x => x.live !== false)

    arr.sort((A, B) => {
      const a = Number.isFinite(A.ts) ? A.ts : Infinity
      const b = Number.isFinite(B.ts) ? B.ts : Infinity
      let d = a - b
      if (SORT_DIR === 'desc') d = -d
      if (d !== 0) return d
      return A.when - B.when
    })

    const $g = $('#igmjq-grid').empty()
    for (const it of arr) {
      const $a = $(
        '<a target="_blank" rel="noopener noreferrer nofollow">'
      ).attr('href', it.href)
      const $img = $('<img alt="">')
      if (it.img) $img.attr('src', it.img)
      $a.append($img)

      $a.append('<div class="igmjq-scrim"></div>')

      if (it.live === false) {
        $a.append('<div class="igmjq-badge">ghost</div>')
      } else if (!Number.isFinite(it.ts)) {
        $a.append('<div class="igmjq-badge">undated</div>')
      }

      // Year overlay - THIS WAS MISSING!
      const yr = Number.isFinite(it.ts) ? new Date(it.ts).getFullYear() : null
      const bucket = yearBucket(yr)
      const $year = $('<div class="igmjq-year">')
        .addClass(bucket)
        .attr('data-year', yr || '')
      $year
        .append('<span class="dot"></span>')
        .append(document.createTextNode(yr ? String(yr) : '—'))
      $a.append($year)

      $g.append($a)
    }
    $('#igmjq-count').text(String(arr.length))
  }

  function renderDebug() {
    const rows = [...items.entries()]
      .map(([sc, it]) => {
        const undated = !Number.isFinite(it.ts)
        const yr = Number.isFinite(it.ts) ? new Date(it.ts).getFullYear() : ''
        return `<tr>
        <td><code>${sc}</code></td>
        <td>${undated ? '<span class="warn">undated</span>' : toIso(it.ts)}</td>
        <td>${it.ts_source || ''}</td>
        <td>${it.ts_raw ?? ''}</td>
        <td>${yr}</td>
        <td>${it.img_source || ''}</td>
        <td>${it.live === false ? 'ghost' : it.live === true ? 'live' : '(pending)'}</td>
      </tr>`
      })
      .join('')
    $('#igmjq-debug').html(`
      <table>
        <thead>
          <tr><th>shortcode</th><th>date</th><th>date source</th><th>date raw</th><th>year</th><th>img source</th><th>status</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `)
  }

  // Route change handler
  function onRouteChange() {
    const next = routeCtx()
    if (next.key === ROUTE.key) return

    ROUTE = next
    STORAGE_KEY = 'igmjq_state::' + ROUTE.key
    updateScopeLabel()

    items.clear()
    restore()

    render()
    renderDebug()
    scanOnce()
  }

  // Patch history for SPA navigation
  ;(function patchHistory() {
    const ev = () => window.dispatchEvent(new Event('locationchange'))
    const _ps = history.pushState
    history.pushState = function () {
      const r = _ps.apply(this, arguments)
      ev()
      return r
    }
    const _rs = history.replaceState
    history.replaceState = function () {
      const r = _rs.apply(this, arguments)
      ev()
      return r
    }
    window.addEventListener('popstate', ev)
    window.addEventListener('locationchange', onRouteChange)
  })()

  // Initialize
  restore()
  render()
  renderDebug()
  scanOnce()

  mo.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['href', 'src', 'srcset'],
  })
})(window.jQuery)
