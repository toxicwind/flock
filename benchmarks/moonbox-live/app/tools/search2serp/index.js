async function search(query){
  const { BrowserEngine } = await import('../shared/BrowserEngine.mjs');
  const engine = await BrowserEngine.create();
  const page = await engine.newPage();
  const url = `https://duckduckgo.com/?q=${encodeURIComponent(query)}&ia=web`;
  await page.goto(url);
  await page.waitForSelector('a.result__a');
  const results = await page.$$eval('a.result__a', els => els.map(a=>({ title:a.textContent.trim(), url:a.href })));
  const out = { results, proxy: engine.proxy, traceFile: engine.traceFile };
  await engine.close();
  return out;
}

module.exports = { search };
