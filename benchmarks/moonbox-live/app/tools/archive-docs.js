#!/usr/bin/env node
const fs = require('node:fs/promises');
const path = require('node:path');
const { spawn } = require('node:child_process');

const MANIFEST_PATH = process.argv[2] || path.join('docs','vendors','_manifest.json');
const VENDOR_DIR = process.env.VENDOR_DOCS_DIR || path.join('docs','vendors');
const KNOWLEDGE_ROOT = process.env.KNOWLEDGE_ROOT || path.join('docs','knowledge');
const CONCURRENCY = parseInt(process.env.CAPTURE_CONCURRENCY || '4',10);
const TIMEOUT = parseInt(process.env.CAPTURE_TIMEOUT_MS || '15000',10);

async function readJson(p){
  return JSON.parse(await fs.readFile(p,'utf-8'));
}
async function writeJson(p,data){
  await fs.mkdir(path.dirname(p),{recursive:true});
  await fs.writeFile(p,JSON.stringify(data,null,2));
}
async function getPkgInfo(name){
  const pkgPath = path.join('node_modules',name,'package.json');
  const raw = await fs.readFile(pkgPath,'utf-8');
  const pkg = JSON.parse(raw);
  return {name,version:pkg.version,license:pkg.license||'',homepage:pkg.homepage||'',repo:(pkg.repository && (typeof pkg.repository==='string'?pkg.repository:pkg.repository.url))||'',source:'npm'};
}
function runWeb2md(url){
  return new Promise((resolve,reject)=>{
    const curl = spawn('curl',['-L',url]);
    const proc = spawn('node',['webpage-to-markdown.js','--stdin',url],{timeout:TIMEOUT});
    let out=''; let err='';
    curl.stdout.pipe(proc.stdin);
    proc.stdout.on('data',d=>{out+=d.toString();});
    proc.stderr.on('data',d=>{err+=d.toString();});
    proc.on('error',reject);
    proc.on('close',code=>{
      if(code!==0){return reject(new Error(err||('web2md exited '+code)));}
      const lines = out.trimEnd().split('\n');
      const hashLine = lines.pop();
      const md = lines.join('\n')+'\n';
      const hash = hashLine.replace('sha256:','').trim();
      resolve({md,hash});
    });
  });
}
async function capturePage(lib,version,page){
  const {md,hash} = await runWeb2md(page.url);
  const libDir = path.join(VENDOR_DIR,lib,version);
  await fs.mkdir(libDir,{recursive:true});
  const filePath = path.join(libDir,`${page.slug}.md`);
  await fs.writeFile(filePath,md);
  const stat = await fs.stat(filePath);
  return {url:page.url,path:filePath,title:md.split('\n')[0].replace(/^#\s*/,'').trim(),sha256:hash,retrieved_at:new Date().toISOString(),size:stat.size};
}
async function runTasks(tasks,limit){
  const ret=[]; const executing=[];
  for(const task of tasks){
    const p=task().then(r=>{executing.splice(executing.indexOf(p),1);return r;});
    ret.push(p); executing.push(p);
    if(executing.length>=limit){ await Promise.race(executing); }
  }
  return Promise.all(ret);
}
async function main(){
  const manifest = await readJson(MANIFEST_PATH);
  const inventory=[]; const knowledgeEntries=[];
  for(const libEntry of manifest.libraries){
    const info = await getPkgInfo(libEntry.name);
    inventory.push(info);
    const tasks = libEntry.pages.map(page=>async()=>{
      const data = await capturePage(info.name,info.version,page);
      knowledgeEntries.push({title:data.title,url:data.url,retrieved_at:data.retrieved_at,summary:data.title,relevant_claims:[],sha256:data.sha256,body_sha256:data.sha256});
      return data;
    });
    const results = await runTasks(tasks,CONCURRENCY);
    await writeJson(path.join(VENDOR_DIR,info.name,info.version,'manifest.json'),results);
  }
  await writeJson(path.join(VENDOR_DIR,'_inventory.json'),inventory);
  const knowledgePath = path.join(KNOWLEDGE_ROOT,'index.jsonl');
  let existing='';
  try{ existing = await fs.readFile(knowledgePath,'utf-8'); }catch{}
  const lines = existing? existing.trimEnd().split('\n') : [];
  for(const k of knowledgeEntries){ lines.push(JSON.stringify(k)); }
  await fs.writeFile(knowledgePath,lines.join('\n')+'\n');
  const sourcesPath = path.join(KNOWLEDGE_ROOT,'sources.md');
  let sources='';
  try{ sources = await fs.readFile(sourcesPath,'utf-8'); }catch{}
  let srcLines = sources ? sources.trimEnd().split('\n') : [];
  for(const k of knowledgeEntries){ srcLines.push(`- [${k.title}](${k.url})`); }
  await fs.writeFile(sourcesPath,srcLines.join('\n')+'\n');
}
main().catch(err=>{console.error(err);process.exit(1);});
