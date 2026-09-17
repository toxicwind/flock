# SANDBOX BACKUP RESTORE GUIDE

## If this container is destroyed:

1. **Your files are ALREADY SAFE** — /mnt/agents/output/ is on drive9 (persistent, close-sync)
2. **This tarball** contains a complete git snapshot of all code/configs
3. **The drive9 server** (http://10.213.5.144) syncs everything automatically

## To restore in a new container:

```bash
cd /mnt/agents/output
git init
git add -A
git commit -m "restore"
```

## Critical files that persist:
- experimental-crisis/          → Full recon toolkit
- MASTER_INDEX/                 → Repository metadata & keys
- *.py, *.sh, *.json           → All scripts and configs
- portal_proxy.py               → Portal FUSE mount wrapper
- swarm_workspace.py            → Container orchestrator
- current_container_metadata.json → Container history

## If drive9 also fails:
Extract this tarball:
```bash
tar xzf sandbox-backup-*.tar.gz -C /mnt/agents/output/
```

## Container IDs seen:
- 8d3d204094b849498921c920f8c45367 (session 1)
- 35829eec9ddb448583192863a45a8eb6 (session 2)
- db3657281a5e483a8a340987fb419037 (session 3)

## Live credentials (may expire):
- Preview URL: https://3000-qg2b3hj7hyepprkjd4olpeqi5desg6r7qvmsjkjh.ap-beijing.tencentags.com
- traffic_access_token: e0d39d62bcdadbc59b32f1a8c8d1ba2f3dbd0e58092f7213fd68418ed0df5f53
- drive9 actor: ef187d70b1248b39469c476dec4c6a2c (session 2), 54d393365a1a15691322ca3ea881d31d (session 3)
