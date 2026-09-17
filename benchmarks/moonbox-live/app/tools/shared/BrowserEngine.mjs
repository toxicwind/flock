import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import os from 'os';
import path from 'path';

chromium.use(StealthPlugin());

function buildProxy(){
  const enabled = process.env.OUTBOUND_PROXY_ENABLED === '1';
  if(!enabled) return { state: { enabled:false } };
  const server = `http://${process.env.OUTBOUND_PROXY_URL}`;
  const username = process.env.OUTBOUND_PROXY_USER;
  const password = process.env.OUTBOUND_PROXY_PASS;
  const proxy = { server, username, password };
  return { state: { enabled:true, server, auth: username && password ? 'present':'absent' }, config: proxy };
}

class BrowserEngine{
  static async create(opts={}){
    const { statePath } = opts;
    const { state:proxyState, config:proxyConfig } = buildProxy();
    const launchOpts = { headless:true };
    if(proxyConfig) launchOpts.proxy = proxyConfig;
    const browser = await chromium.launch(launchOpts);
    const ctxOpts = { ignoreHTTPSErrors:true };
    if(statePath) ctxOpts.storageState = statePath;
    const context = await browser.newContext(ctxOpts);
    const traceFile = path.join(os.tmpdir(), `trace-${Date.now()}.zip`);
    await context.tracing.start({ screenshots:true, snapshots:true });
    const engine = new BrowserEngine(browser, context, proxyState, traceFile);
    return engine;
  }

  static async fromState(path, opts={}){
    return BrowserEngine.create({ ...opts, statePath: path });
  }

  constructor(browser, context, proxy, traceFile){
    this.browser = browser;
    this.context = context;
    this.proxy = proxy;
    this.traceFile = traceFile;
  }

  async newPage(){
    return await this.context.newPage();
  }

  async saveState(file){
    await this.context.storageState({ path: file });
  }

  async close(){
    await this.context.tracing.stop({ path: this.traceFile });
    await this.context.close();
    await this.browser.close();
  }
}

export { BrowserEngine };
