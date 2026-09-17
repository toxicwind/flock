#!/usr/bin/env node
const fs = require('node:fs/promises');
const path = require('node:path');
const { fetchWithBrowser } = require('./index');

function parseArgs(){
  const args = process.argv.slice(2);
  const urls=[];
  for(const a of args){ if(!a.startsWith('--')) urls.push(a); }
  return {urls};
}

async function main(){
  const {urls}=parseArgs();
  if(urls.length===0){
    console.error('usage: web2md <url> [url...]');
    process.exit(1);
  }
  const results=[];
  for(const url of urls){
    try{
      const r = await fetchWithBrowser(url);
      console.log('proxy.state', r.proxy);
      console.log('traceFile', r.traceFile);
      const host = new URL(url).hostname;
      const ts = Date.now().toString();
      const dir = path.join('tmp','web2md-diag',host,ts);
      await fs.mkdir(dir,{recursive:true});
      await fs.writeFile(path.join(dir,'page.raw.html'),r.html);
      await fs.writeFile(path.join(dir,'page.norm.md'),r.markdown);
      await fs.writeFile(path.join(dir,'diag.json'),JSON.stringify({url,traceFile:r.traceFile,proxy:r.proxy},null,2));
      const size = r.html.length;
      const textLen = r.markdown.length;
      const status = size>1024 || textLen>2048 ? 'ok':'too-small';
      results.push({url,status,bytes:size,text:textLen,dir});
      if(status==='too-small') process.exitCode=2;
    }catch(err){
      console.error('fail',url,err.message);
      results.push({url,error:err.message});
      process.exitCode=1;
    }
  }
  console.table(results);
  results.forEach(r=>{ if(r.dir) console.log('saved',r.url,'->',r.dir); });
}

main();
