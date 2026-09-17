#!/usr/bin/env node
const { search } = require('./index');

async function main(){
  const query = process.argv.slice(2).join(' ');
  if(!query){
    console.error('usage: search2serp <query>');
    process.exit(1);
  }
  const res = await search(query);
  console.log('proxy.state', res.proxy);
  console.log('traceFile', res.traceFile);
  console.table(res.results);
}

main();
