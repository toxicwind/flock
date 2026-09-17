const { JSDOM } = require('jsdom');
const { Readability } = require('@mozilla/readability');
const TurndownService = require('turndown');

function stripTracking(u){
  const url = new URL(u);
  for(const k of [...url.searchParams.keys()]){
    if(/^utm_/.test(k) || k==='fbclid') url.searchParams.delete(k);
  }
  return url.toString();
}

function normalizeHTML(html,url){
  const dom = new JSDOM(html,{url});
  const doc = dom.window.document;
  const links = doc.querySelectorAll('a[href]');
  links.forEach(a=>{ try{ a.href = stripTracking(a.href); }catch{} });
  const reader = new Readability(doc);
  const article = reader.parse();
  const turndown = new TurndownService({ headingStyle: 'atx' });
  const source = article && article.content ? article.content : doc.body.innerHTML;
  const md = turndown.turndown(source).replace(/\s+/g,' ').trim();
  return md;
}

async function fetchWithBrowser(url){
  const { BrowserEngine } = await import('../shared/BrowserEngine.mjs');
  const engine = await BrowserEngine.create();
  const page = await engine.newPage();
  await page.goto(url, { waitUntil:'networkidle' });
  const html = await page.content();
  const markdown = normalizeHTML(html,url);
  const result = { html, markdown, proxy: engine.proxy, traceFile: engine.traceFile };
  await engine.close();
  return result;
}

module.exports = { fetchWithBrowser, fetchWithFallback: fetchWithBrowser };
