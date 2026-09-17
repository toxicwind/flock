#!/usr/bin/env python3
import sys, json
O,A,B=sys.argv[1],sys.argv[2],sys.argv[3]
def n(l):
  l=l.strip()
  if not l: return None
  try: return json.dumps(json.loads(l),ensure_ascii=False,sort_keys=True,separators=(",",":"))
  except Exception: return l
def lines(p):
  with open(p,"r",encoding="utf-8",errors="replace") as f:
    for l in f:
      nl=n(l)
      if nl is not None: yield nl
s=set();o=[]
for p in (A,B):
  for l in lines(p):
    if l not in s: s.add(l); o.append(l)
with open(A,"w",encoding="utf-8") as f:
  if o: f.write("\n".join(o)+"\n")
sys.exit(0)
