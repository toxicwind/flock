#!/usr/bin/env python3
import sys, json
def k(x):
  try: return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
  except Exception: return str(x)
def u(a,b):
  s=set();o=[]
  for it in a:
    kk=k(it)
    if kk not in s: s.add(kk); o.append(it)
  for it in b:
    kk=k(it)
    if kk not in s: s.add(kk); o.append(it)
  return o
def m(a,b):
  if isinstance(a,dict) and isinstance(b,dict):
    o=dict(a)
    for kk,v in b.items():
      if kk not in o: o[kk]=v
      else:
        aa=o[kk]
        if isinstance(aa,dict) and isinstance(v,dict): o[kk]=m(aa,v)
        elif isinstance(aa,list) and isinstance(v,list): o[kk]=u(aa,v)
        else: o[kk]=aa
    return o
  if isinstance(a,list) and isinstance(b,list): return u(a,b)
  return a
O,A,B=sys.argv[1],sys.argv[2],sys.argv[3]
try:
  with open(A,"r",encoding="utf-8",errors="replace") as f: ao=json.load(f)
  with open(B,"r",encoding="utf-8",errors="replace") as f: bo=json.load(f)
  out=m(ao,bo)
  with open(A,"w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,indent=2,sort_keys=True); f.write("\n")
  sys.exit(0)
except Exception:
  sys.exit(1)
