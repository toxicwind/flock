#!/usr/bin/env node
const { webpageToMarkdown, htmlToMarkdown } = require('./lib/webpageToMarkdown');
const crypto = require('node:crypto');

async function main() {
  const arg = process.argv[2];
  if (!arg) {
    console.error('Usage: node webpage-to-markdown.js <URL> or --stdin <URL>');
    process.exit(1);
  }
  if (arg === '--stdin') {
    const url = process.argv[3] || 'about:blank';
    let html='';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data',chunk=>html+=chunk);
    process.stdin.on('end',()=>{
      try {
        const md = htmlToMarkdown(html,url);
        const hash = crypto.createHash('sha256').update(md).digest('hex');
        console.log(md);
        console.log(`sha256:${hash}`);
      } catch(err){
        console.error(err.message);
        process.exit(1);
      }
    });
  } else {
    const url = arg;
    try {
      const md = await webpageToMarkdown(url);
      const hash = crypto.createHash('sha256').update(md).digest('hex');
      console.log(md);
      console.log(`sha256:${hash}`);
    } catch (err) {
      console.error(err.message);
      process.exit(1);
    }
  }
}

main();
