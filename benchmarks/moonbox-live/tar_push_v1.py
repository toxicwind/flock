#!/usr/bin/env python3
"""tar_push_v1.py — push repos as tar.gz via GitHub Releases API (bypasses git TLS flakiness)."""
import os, sys, subprocess, json, base64, tarfile, tempfile, urllib.request

GH_PAT = os.environ.get('GITHUB_PAT','')
if not GH_PAT:
    try: GH_PAT = open('/mnt/agents/.secrets/github_pat').read().strip()
    except: pass

HDR = {
    'Authorization': f'token {GH_PAT}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'tar-push-v1',
}

def run(cmd,t=30):
    r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=t)
    return r.returncode==0,r.stdout,r.stderr

def tar_repo(src,out):
    with tarfile.open(out,'w:gz') as tf:
        for it in os.listdir(src):
            if it=='.git': continue
            tf.add(os.path.join(src,it),arcname=it)
    return out

def api_req(url,method='GET',data=None,ct=None):
    h={**HDR}
    if ct: h['Content-Type']=ct
    req=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            return resp.status,resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode()
    except Exception as e:
        return -1,str(e)

def get_or_create_release(owner,repo,tag):
    # try existing
    st,body=api_req(f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}")
    if st==200:
        return json.loads(body).get('id')
    # create
    st,body=api_req(f"https://api.github.com/repos/{owner}/{repo}/releases",
        method='POST',
        data=json.dumps({"tag_name":tag,"name":tag,"body":"auto"}).encode(),
        ct='application/json')
    if st in (200,201):
        return json.loads(body).get('id')
    print(f"[!] release err {st}: {body[:200]}")
    return None

def upload_asset(owner,repo,release_id,filepath):
    url=f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets?name={os.path.basename(filepath)}"
    with open(filepath,'rb') as f:
        data=f.read()
    st,body=api_req(url,method='POST',data=data,ct='application/gzip')
    print(f"[{'+' if st in (200,201) else '!'}] {os.path.basename(filepath)} -> {st}")
    return st in (200,201)

def split_upload(filepath,chunk_mb=80):
    chunk=chunk_mb*1024*1024
    parts=[]
    with open(filepath,'rb') as f:
        idx=0
        while True:
            buf=f.read(chunk)
            if not buf: break
            pn=f"{filepath}.part{idx:03d}"
            with open(pn,'wb') as p: p.write(buf)
            parts.append(pn); idx+=1
    return parts

def push(owner,repo,srcdir,tag="archive"):
    with tempfile.TemporaryDirectory() as td:
        tar=os.path.join(td,f"{repo}.tar.gz")
        tar_repo(srcdir,tar)
        sz=os.path.getsize(tar)
        print(f"[*] tar {sz} bytes")
        rid=get_or_create_release(owner,repo,tag)
        if not rid:
            return False
        if sz>90*1024*1024:
            print("[*] splitting...")
            for pt in split_upload(tar):
                upload_asset(owner,repo,rid,pt)
        else:
            upload_asset(owner,repo,rid,tar)
        return True

if __name__=="__main__":
    if len(sys.argv)<4:
        print("Usage: python3 tar_push_v1.py <owner> <repo> <srcdir> [tag]")
        sys.exit(1)
    push(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4] if len(sys.argv)>4 else "archive")
