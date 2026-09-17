#!/usr/bin/env node
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

const VENDOR_DIR = process.env.VENDOR_DOCS_DIR || path.join('docs','vendors');
async function main(){
  const inventory = JSON.parse(await fs.readFile(path.join(VENDOR_DIR,'_inventory.json'),'utf-8'));
  for(const lib of inventory){
    const manifestPath = path.join(VENDOR_DIR,lib.name,lib.version,'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath,'utf-8'));
    let changed=false;
    for(const page of manifest){
      const data = await fs.readFile(page.path);
      const hash = crypto.createHash('sha256').update(data).digest('hex');
      if(page.sha256!==hash){ page.sha256=hash; changed=true; }
    }
    if(changed){ await fs.writeFile(manifestPath,JSON.stringify(manifest,null,2)); }
  }
  console.log('docs validated');
}
main().catch(err=>{console.error(err);process.exit(1);});
