#!/usr/bin/env python3
"""drive9_client_v2.py — Native Drive9 API client.
Uses the actual HTTP/gRPC-ish API instead of filesystem operations.
Endpoints discovered from /usr/local/bin/drive9 strings + log analysis.
"""
import os, json, urllib.request, urllib.error, urllib.parse, sys, pathlib, time
from typing import Optional, Dict, Any, List

class Drive9Client:
    def __init__(
        self,
        server: str = "http://10.213.5.144",
        token: Optional[str] = None,
        project: str = "19fd6126-0bc2-8dfe-8000-0e510dd7d34d",
        tenant: str = "f03cbd12-eb66-421c-b4c4-eed73c0bc4bf",
    ):
        self.server = server.rstrip("/")
        self.project = project
        self.tenant = tenant
        self.token = token or os.environ.get("DRIVE9_TOKEN", "")
        self.actor = os.environ.get("DRIVE9_ACTOR", "2583cb75416b04bd5c61446f2d5934fe")
        self._opener = urllib.request.build_opener()

    def _hdr(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Dat9-Actor": self.actor,
            "X-Dat9-Tenant": self.tenant,
            "Accept": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def _req(self, method: str, path: str, body: Optional[bytes] = None, hdrs: Optional[Dict[str, str]] = None) -> tuple:
        url = f"{self.server}{path}"
        req = urllib.request.Request(url, data=body, headers=self._hdr(hdrs), method=method)
        try:
            with self._opener.open(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            return -1, str(e)

    # === FS Operations ===
    def fs_batch_stat(self, paths: List[str]) -> tuple:
        """Batch stat files."""
        body = json.dumps({"paths": paths, "project": self.project}).encode()
        return self._req("POST", "/v1/fs:batch-stat", body)

    def fs_batch_read(self, paths: List[str]) -> tuple:
        """Batch read small files."""
        body = json.dumps({"paths": paths, "project": self.project}).encode()
        return self._req("POST", "/v1/fs:batch-read-small", body)

    def fs_batch_write(self, files: Dict[str, str]) -> tuple:
        """Batch write files. {path: base64_content}"""
        body = json.dumps({"files": files, "project": self.project}).encode()
        return self._req("POST", "/v1/fs:batch-write", body)

    def fs_list(self, path: str = "/") -> tuple:
        """List directory contents."""
        q = urllib.parse.urlencode({"path": path, "project": self.project})
        return self._req("GET", f"/v1/fs?{q}")

    def fs_mkdir(self, path: str, mode: int = 0o755) -> tuple:
        """Create directory."""
        body = json.dumps({"path": path, "mode": mode, "project": self.project}).encode()
        return self._req("POST", "/v1/fs:mkdir", body)

    # === Journal Operations ===
    def journal_list(self) -> tuple:
        """List journals for project."""
        q = urllib.parse.urlencode({"project": self.project})
        return self._req("GET", f"/v1/journals?{q}")

    def journal_read(self, journal_id: str, offset: int = 0, limit: int = 100) -> tuple:
        """Read journal entries."""
        q = urllib.parse.urlencode({
            "project": self.project,
            "journal": journal_id,
            "offset": offset,
            "limit": limit,
        })
        return self._req("GET", f"/v1/journal-entries?{q}")

    def journal_append(self, journal_id: str, entries: List[Dict]) -> tuple:
        """Append entries to journal."""
        body = json.dumps({
            "project": self.project,
            "journal": journal_id,
            "entries": entries,
        }).encode()
        return self._req("POST", "/v1/journal-entries", body)

    def journal_create(self, name: str, description: str = "") -> tuple:
        """Create new journal."""
        body = json.dumps({
            "project": self.project,
            "name": name,
            "description": description,
        }).encode()
        return self._req("POST", "/v1/journals", body)

    # === Upload Operations ===
    def upload_init(self, path: str, size: int) -> tuple:
        """Initialize multipart upload."""
        body = json.dumps({
            "project": self.project,
            "path": path,
            "size": size,
        }).encode()
        return self._req("POST", "/v1/uploads", body)

    def upload_status(self, upload_id: str) -> tuple:
        """Check upload status."""
        q = urllib.parse.urlencode({"project": self.project, "upload": upload_id})
        return self._req("GET", f"/v1/uploads?{q}")

    # === Git Workspace Operations ===
    def git_list(self) -> tuple:
        """List git workspaces."""
        q = urllib.parse.urlencode({"project": self.project})
        return self._req("GET", f"/v1/git-workspaces?{q}")

    def git_tree(self, workspace: str, ref: str = "HEAD") -> tuple:
        """Get git tree."""
        q = urllib.parse.urlencode({"project": self.project, "workspace": workspace, "ref": ref})
        return self._req("GET", f"/v1/git-workspaces/tree?{q}")

    # === Quota ===
    def quota(self) -> tuple:
        """Get project quota."""
        q = urllib.parse.urlencode({"project": self.project})
        return self._req("GET", f"/quota/v1/fs?{q}")

    # === Health ===
    def health(self) -> tuple:
        return self._req("GET", "/health")


def main():
    c = Drive9Client()
    print(f"[*] Drive9 Client v2")
    print(f"[*] Server: {c.server}")
    print(f"[*] Project: {c.project}")

    # Probe endpoints
    endpoints = [
        ("health", lambda: c.health()),
        ("quota", lambda: c.quota()),
        ("fs_list(/)", lambda: c.fs_list("/")),
        ("journal_list", lambda: c.journal_list()),
        ("git_list", lambda: c.git_list()),
    ]

    for name, fn in endpoints:
        status, body = fn()
        print(f"[{status}] {name}: {body[:200]}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
