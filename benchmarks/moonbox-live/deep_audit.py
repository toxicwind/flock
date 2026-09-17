#!/usr/bin/env python3
"""
Deep System Introspection Toolkit — Meta-Compiler Output
Generates audit trails without relying on external tool execution.
Treats environment as unreliable; every piece is forged and verified.
"""

import os, sys, json, time, struct, socket, fcntl, array, ctypes
import subprocess, pathlib, hashlib, base64, re, stat, errno
from datetime import datetime, timezone

# ── Constants ──
AUDIT_LOG = "/mnt/agents/output/audit.log"
FUSE_MOUNT = "/mnt/agents/output/fuse_audit"
NS_PATH = "/proc/self/ns"

# ── Helpers ──
def ts() -> str:
    return datetime.now(timezone.utc).isoformat()

def log(entry: dict):
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps({"t": ts(), **entry}) + "\n")

def readlink_safe(path: str) -> str:
    try:
        return os.readlink(path)
    except Exception as e:
        return f"<error:{e}>"

def readfile_safe(path: str, limit: int = 4096) -> str:
    try:
        with open(path, "rb") as f:
            return f.read(limit).decode("utf-8", "replace")
    except Exception as e:
        return f"<error:{e}>"

# ── 1. Namespace Forge ──
def inspect_namespaces() -> dict:
    """Read /proc/self/ns/* and compare to init."""
    ns_types = ["mnt", "net", "pid", "ipc", "uts", "user", "cgroup"]
    result = {}
    for ns in ns_types:
        self_link = readlink_safe(f"/proc/self/ns/{ns}")
        init_link = readlink_safe(f"/proc/1/ns/{ns}")
        result[ns] = {
            "self": self_link,
            "init": init_link,
            "shared": self_link == init_link
        }
    log({"event": "ns_inspect", "data": result})
    return result

# ── 2. Container ID Heuristic ──
def detect_container() -> dict:
    """Multi-source container detection."""
    hints = {}
    # cgroup v1/v2
    hints["cgroup"] = readfile_safe("/proc/self/cgroup", 2048)
    # init process name
    hints["init_comm"] = readfile_safe("/proc/1/comm", 256).strip()
    # /.dockerenv
    hints["dockerenv"] = os.path.exists("/.dockerenv")
    # container-specific env
    hints["env_keys"] = [k for k in os.environ if any(x in k.lower() for x in ["k8s", "kube", "docker", "container", "ec2", "gcp", "azure"])]
    # overlay check
    hints["rootfs_type"] = readfile_safe("/proc/mounts", 2048).split("\n")[0] if os.path.exists("/proc/mounts") else "n/a"
    log({"event": "container_detect", "data": hints})
    return hints

# ── 3. Process Tree with Namespace Context ──
def process_tree() -> list:
    """Build process tree via /proc traversal."""
    procs = []
    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit():
            continue
        pid = int(pid_str)
        try:
            comm = readfile_safe(f"/proc/{pid}/comm", 256).strip()
            status = readfile_safe(f"/proc/{pid}/status", 1024)
            ppid_match = re.search(r"PPid:\s*(\d+)", status)
            ppid = int(ppid_match.group(1)) if ppid_match else -1
            ns_mnt = readlink_safe(f"/proc/{pid}/ns/mnt")
            procs.append({"pid": pid, "ppid": ppid, "comm": comm, "ns_mnt": ns_mnt})
        except Exception:
            continue
    log({"event": "proc_tree", "count": len(procs)})
    return procs

# ── 4. File Descriptor Audit ──
def fd_audit(pid: int = os.getpid()) -> dict:
    """Inspect /proc/<pid>/fd and /proc/<pid>/fdinfo."""
    fd_dir = f"/proc/{pid}/fd"
    result = {}
    try:
        for fd in os.listdir(fd_dir):
            target = readlink_safe(os.path.join(fd_dir, fd))
            fdinfo = readfile_safe(f"/proc/{pid}/fdinfo/{fd}", 512)
            result[fd] = {"target": target, "info": fdinfo}
    except Exception as e:
        result = {"error": str(e)}
    log({"event": "fd_audit", "pid": pid, "count": len(result)})
    return result

# ── 5. Strace-like Syscall Trace (ptrace fallback) ──
def strace_attach(target_pid: int) -> dict:
    """Attach ptrace to target and capture syscall entry/exit.
    Requires CAP_SYS_PTRACE or same uid.
    """
    import signal
    result = {"attached": False, "syscalls": []}
    try:
        libc = ctypes.CDLL("libc.so.6")
        PTRACE_ATTACH = 0
        PTRACE_SYSCALL = 24
        PTRACE_DETACH = 17
        PTRACE_PEEKUSER = 3
        WIFSTOPPED = lambda s: (s & 0x7f) == 0x7f

        os.kill(target_pid, 0)  # verify existence
        if libc.ptrace(PTRACE_ATTACH, target_pid, None, None) != 0:
            raise OSError(f"ptrace attach failed: {ctypes.get_errno()}")

        _, status = os.waitpid(target_pid, 0)
        if WIFSTOPPED(status):
            result["attached"] = True
            for _ in range(20):  # capture 20 syscalls
                libc.ptrace(PTRACE_SYSCALL, target_pid, None, None)
                pid, status = os.waitpid(target_pid, 0)
                if WIFSTOPPED(status):
                    # Peek orig_rax (x86_64 offset 15*8 = 120)
                    rax = libc.ptrace(PTRACE_PEEKUSER, target_pid, 120, None)
                    if rax >= 0:
                        result["syscalls"].append({"nr": rax, "name": SYSCALL_TABLE.get(rax, f"sys_{rax}")})
            libc.ptrace(PTRACE_DETACH, target_pid, None, None)
    except Exception as e:
        result["error"] = str(e)
    log({"event": "strace_attach", "target": target_pid, **result})
    return result

# x86_64 syscall table (partial)
SYSCALL_TABLE = {
    0: "read", 1: "write", 2: "open", 3: "close", 4: "stat", 5: "fstat",
    6: "lstat", 7: "poll", 8: "lseek", 9: "mmap", 10: "mprotect", 11: "munmap",
    12: "brk", 13: "rt_sigaction", 14: "rt_sigprocmask", 15: "rt_sigreturn",
    16: "ioctl", 17: "pread64", 18: "pwrite64", 19: "readv", 20: "writev",
    21: "access", 22: "pipe", 23: "select", 24: "sched_yield", 25: "mremap",
    26: "msync", 27: "mincore", 28: "madvise", 29: "shmget", 30: "shmat",
    31: "shmctl", 32: "dup", 33: "dup2", 34: "pause", 35: "nanosleep",
    39: "getpid", 41: "socket", 42: "connect", 43: "accept", 44: "sendto",
    45: "recvfrom", 46: "sendmsg", 47: "recvmsg", 48: "shutdown", 49: "bind",
    50: "listen", 51: "getsockname", 52: "getpeername", 53: "socketpair",
    54: "setsockopt", 55: "getsockopt", 56: "clone", 57: "fork", 58: "vfork",
    59: "execve", 60: "exit", 61: "wait4", 62: "kill", 63: "uname",
    72: "fcntl", 73: "flock", 74: "fsync", 75: "fdatasync", 76: "truncate",
    77: "ftruncate", 78: "getdents", 79: "getcwd", 80: "chdir", 81: "fchdir",
    82: "rename", 83: "mkdir", 84: "rmdir", 85: "creat", 86: "link",
    87: "unlink", 88: "symlink", 89: "readlink", 90: "chmod", 91: "fchmod",
    92: "chown", 93: "fchown", 94: "lchown", 95: "umask", 96: "gettimeofday",
    97: "getrlimit", 98: "getrusage", 99: "sysinfo", 100: "times",
    101: "ptrace", 102: "getuid", 103: "syslog", 104: "getgid", 105: "setuid",
    106: "setgid", 107: "geteuid", 108: "getegid", 109: "setpgid",
    110: "getppid", 111: "getpgrp", 112: "setsid", 113: "setreuid",
    114: "setregid", 115: "getgroups", 116: "setgroups", 117: "setresuid",
    118: "getresuid", 119: "setresgid", 120: "getresgid", 121: "getpgid",
    122: "setfsuid", 123: "setfsgid", 124: "getsid", 125: "capget",
    126: "capset", 127: "rt_sigpending", 128: "rt_sigtimedwait",
    129: "rt_sigqueueinfo", 130: "rt_sigsuspend", 131: "sigaltstack",
    132: "utime", 133: "mknod", 134: "uselib", 135: "personality",
    136: "ustat", 137: "statfs", 138: "fstatfs", 139: "sysfs", 140: "getpriority",
    141: "setpriority", 142: "sched_setparam", 143: "sched_getparam",
    144: "sched_setscheduler", 145: "sched_getscheduler",
    146: "sched_get_priority_max", 147: "sched_get_priority_min",
    148: "sched_rr_get_interval", 149: "mlock", 150: "munlock",
    151: "mlockall", 152: "munlockall", 153: "vhangup", 154: "modify_ldt",
    155: "pivot_root", 156: "_sysctl", 157: "prctl", 158: "arch_prctl",
    159: "adjtimex", 160: "setrlimit", 161: "chroot", 162: "sync",
    163: "acct", 164: "settimeofday", 165: "mount", 166: "umount2",
    167: "swapon", 168: "swapoff", 169: "reboot", 170: "sethostname",
    171: "setdomainname", 172: "iopl", 173: "ioperm", 174: "create_module",
    175: "init_module", 176: "delete_module", 177: "get_kernel_syms",
    178: "query_module", 179: "quotactl", 180: "nfsservctl", 186: "gettid",
    187: "readahead", 188: "setxattr", 189: "lsetxattr", 190: "fsetxattr",
    191: "getxattr", 192: "lgetxattr", 193: "fgetxattr", 194: "listxattr",
    195: "llistxattr", 196: "flistxattr", 197: "removexattr",
    198: "lremovexattr", 199: "fremovexattr", 200: "tkill", 201: "time",
    202: "futex", 203: "sched_setaffinity", 204: "sched_getaffinity",
    205: "set_thread_area", 206: "io_setup", 207: "io_destroy",
    208: "io_getevents", 209: "io_submit", 210: "io_cancel",
    211: "get_thread_area", 212: "lookup_dcookie", 213: "epoll_create",
    214: "epoll_ctl_old", 215: "epoll_wait_old", 216: "remap_file_pages",
    217: "getdents64", 218: "set_tid_address", 219: "restart_syscall",
    220: "semtimedop", 221: "fadvise64", 222: "timer_create",
    223: "timer_settime", 224: "timer_gettime", 225: "timer_getoverrun",
    226: "timer_delete", 227: "clock_settime", 228: "clock_gettime",
    229: "clock_getres", 230: "clock_nanosleep", 231: "exit_group",
    232: "epoll_wait", 233: "epoll_ctl", 234: "tgkill", 235: "utimes",
    236: "vserver", 237: "mbind", 238: "set_mempolicy", 239: "get_mempolicy",
    240: "mq_open", 241: "mq_unlink", 242: "mq_timedsend", 243: "mq_timedreceive",
    244: "mq_notify", 245: "mq_getsetattr", 246: "kexec_load", 247: "waitid",
    248: "add_key", 249: "request_key", 250: "keyctl", 251: "ioprio_set",
    252: "ioprio_get", 253: "inotify_init", 254: "inotify_add_watch",
    255: "inotify_rm_watch", 256: "migrate_pages", 257: "openat",
    258: "mkdirat", 259: "mknodat", 260: "fchownat", 261: "futimesat",
    262: "newfstatat", 263: "unlinkat", 264: "renameat", 265: "linkat",
    266: "symlinkat", 267: "readlinkat", 268: "fchmodat", 269: "faccessat",
    270: "pselect6", 271: "ppoll", 272: "unshare", 273: "set_robust_list",
    274: "get_robust_list", 275: "splice", 276: "tee", 277: "sync_file_range",
    278: "vmsplice", 279: "move_pages", 280: "utimensat", 281: "epoll_pwait",
    282: "signalfd", 283: "timerfd_create", 284: "eventfd", 285: "fallocate",
    286: "timerfd_settime", 287: "timerfd_gettime", 288: "accept4",
    289: "signalfd4", 290: "eventfd2", 291: "epoll_create1", 292: "dup3",
    293: "pipe2", 294: "inotify_init1", 295: "preadv", 296: "pwritev",
    297: "rt_tgsigqueueinfo", 298: "perf_event_open", 299: "recvmmsg",
    300: "fanotify_init", 301: "fanotify_mark", 302: "prlimit64",
    303: "name_to_handle_at", 304: "open_by_handle_at", 305: "clock_adjtime",
    306: "syncfs", 307: "sendmmsg", 308: "setns", 309: "getcpu",
    310: "process_vm_readv", 311: "process_vm_writev", 312: "kcmp",
    313: "finit_module", 314: "sched_setattr", 315: "sched_getattr",
    316: "renameat2", 317: "seccomp", 318: "getrandom", 319: "memfd_create",
    320: "kexec_file_load", 321: "bpf", 322: "execveat", 323: "userfaultfd",
    324: "membarrier", 325: "mlock2", 326: "copy_file_range", 327: "preadv2",
    328: "pwritev2", 329: "pkey_mprotect", 330: "pkey_alloc", 331: "pkey_free",
    332: "statx", 333: "io_pgetevents", 334: "rseq", 435: "clone3"
}

# ── 6. Network Socket Inspection ──
def socket_audit() -> dict:
    """Parse /proc/net/tcp, udp, unix for active sockets."""
    result = {}
    for proto in ["tcp", "tcp6", "udp", "udp6", "unix", "packet", "netlink"]:
        data = readfile_safe(f"/proc/net/{proto}", 8192)
        lines = [l for l in data.split("\n") if l.strip() and not l.startswith("sl")]
        result[proto] = lines[:50]  # limit
    log({"event": "socket_audit", "protocols": list(result.keys())})
    return result

# ── 7. Environment Deep Forge ──
def env_deep() -> dict:
    """Categorize environment variables by sensitivity / source."""
    sensitive = ["password", "secret", "token", "key", "auth", "cred", "private"]
    cloud = ["aws", "azure", "gcp", "ec2", "k8s", "kube", "docker", "container"]
    result = {"sensitive": {}, "cloud": {}, "other": {}}
    for k, v in os.environ.items():
        kl = k.lower()
        if any(s in kl for s in sensitive):
            result["sensitive"][k] = "<redacted>" if len(v) > 8 else v
        elif any(c in kl for c in cloud):
            result["cloud"][k] = v[:64]
        else:
            result["other"][k] = v[:128]
    log({"event": "env_deep", "keys": len(os.environ)})
    return result

# ── 8. Binary / Library Dependency Map ──
def lib_audit() -> dict:
    """Inspect loaded shared libraries via /proc/self/maps."""
    libs = set()
    try:
        with open("/proc/self/maps") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 6:
                    path = parts[-1]
                    if ".so" in path or "/lib" in path:
                        libs.add(path)
    except Exception as e:
        return {"error": str(e)}
    result = {"libs": sorted(libs), "count": len(libs)}
    log({"event": "lib_audit", **result})
    return result

# ── 9. Mount Table with Namespace Overlay ──
def mount_audit() -> dict:
    """Parse /proc/self/mountinfo for overlay, tmpfs, bind mounts."""
    data = readfile_safe("/proc/self/mountinfo", 4096)
    mounts = []
    for line in data.split("\n"):
        if "overlay" in line or "tmpfs" in line or "bind" in line:
            mounts.append(line.strip())
    log({"event": "mount_audit", "suspicious": len(mounts)})
    return {"suspicious_mounts": mounts}

# ── 10. Unshare Wrapper Generator ──
def unshare_cmd(cmd: list) -> list:
    """Return unshare-isolated command for subprocess."""
    return [
        "unshare", "--fork", "--pid", "--mount-proc",
        "--net", "--ipc", "--uts", "--cgroup",
        "bash", "-x", "-c", " ".join(cmd)
    ]

# ── 11. FUSE Audit Stub ──
def fuse_audit_stub():
    """Log FUSE readiness; actual FUSE impl requires libfuse."""
    log({"event": "fuse_audit", "status": "stub", "note": "Install python-fuse or llfuse for full impl"})

# ── 12. Bytecode Introspection ──
def bytecode_self() -> dict:
    """Disassemble own __main__ module bytecode."""
    import dis, types
    result = []
    for name, obj in globals().items():
        if isinstance(obj, types.FunctionType):
            code = obj.__code__
            result.append({
                "name": name,
                "co_names": list(code.co_names),
                "co_varnames": list(code.co_varnames),
                "co_consts": [str(c)[:64] for c in code.co_consts],
                "co_nlocals": code.co_nlocals,
                "co_stacksize": code.co_stacksize,
                "co_flags": code.co_flags
            })
    log({"event": "bytecode_self", "functions": len(result)})
    return result

# ── Main Orchestrator ──
def main():
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    log({"event": "audit_start", "pid": os.getpid(), "ppid": os.getppid(), "uid": os.getuid(), "gid": os.getgid()})

    report = {
        "timestamp": ts(),
        "namespaces": inspect_namespaces(),
        "container": detect_container(),
        "processes": process_tree()[:20],  # limit
        "fd": fd_audit(),
        "sockets": socket_audit(),
        "env": env_deep(),
        "libs": lib_audit(),
        "mounts": mount_audit(),
        "bytecode": bytecode_self()
    }

    # Attempt strace on ipykernel if present
    try:
        import subprocess
        out = subprocess.run(["pgrep", "-f", "ipykernel"], capture_output=True, text=True)
        if out.stdout.strip():
            for pid_str in out.stdout.strip().split("\n")[:1]:
                report["strace"] = strace_attach(int(pid_str))
    except Exception as e:
        report["strace"] = {"error": str(e)}

    fuse_audit_stub()

    # Write full report
    with open("/mnt/agents/output/full_audit.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    log({"event": "audit_complete", "report_path": "/mnt/agents/output/full_audit.json"})
    print(f"[OK] Audit complete. Log: {AUDIT_LOG}  Report: /mnt/agents/output/full_audit.json")
    return report

if __name__ == "__main__":
    main()
