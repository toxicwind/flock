#!/usr/bin/env node
const fs = require('node:fs/promises');
const path = require('node:path');

const VENDOR_DIR = process.env.VENDOR_DOCS_DIR || path.join('docs','vendors');
async function main(){
  const inventory = JSON.parse(await fs.readFile(path.join(VENDOR_DIR,'_inventory.json'),'utf-8'));
  let md = '# Vendor Documentation Index\n\n| Library | Version | Pages | Last Retrieved | Manifest |\n|---|---|---|---|---|\n';
  for(const lib of inventory){
    const manifestPath = path.join(VENDOR_DIR,lib.name,lib.version,'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath,'utf-8'));
    const pages = manifest.length;
    const last = manifest.map(p=>p.retrieved_at).sort().pop();
    const relManifest = path.relative('docs/vendors',manifestPath);
    md += `| ${lib.name} | ${lib.version} | ${pages} | ${last} | [manifest](${relManifest}) |\n`;
  }
  await fs.writeFile(path.join(VENDOR_DIR,'index.md'),md);
}
main().catch(err=>{console.error(err);process.exit(1);});
