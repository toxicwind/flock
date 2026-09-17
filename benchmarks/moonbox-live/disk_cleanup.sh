#!/bin/bash
# === DISK CLEANUP SCRIPT ===
# Based on your system: toxic's cache (117G), /var/cache (19G), .local/share (19G), /tmp (12G)

set -euo pipefail

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'
log() { echo -e "${C}[CLEAN]${N} $1"; }
ok()  { echo -e "${G}[OK]${N} $1"; }
warn(){ echo -e "${Y}[WARN]${N} $1"; }
err() { echo -e "${R}[ERR]${N} $1"; }

DRY_RUN=${DRY_RUN:-1}
run() {
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "  [DRY-RUN] would run: $*"
    else
        echo "  [EXEC] $*"
        "$@"
    fi
}

# --- 1. CACHE CLEANUP ---
log "=== CACHE CLEANUP ==="

# User caches
for user in /home/*; do
    [[ -d "$user" ]] || continue
    un=$(basename "$user")

    # .cache (your 117G monster)
    if [[ -d "$user/.cache" ]]; then
        cache_size=$(du -sh "$user/.cache" 2>/dev/null | cut -f1)
        log "User $un .cache: $cache_size"

        # Safe to delete: pip, npm, yarn, cargo, go-build, hugo, thumbnailers, fontconfig
        for sub in pip npm yarn cargo go-build hugo thumbnails fontconfig mesa_shader_cache; do
            if [[ -d "$user/.cache/$sub" ]]; then
                sz=$(du -sh "$user/.cache/$sub" 2>/dev/null | cut -f1)
                warn "  Removing $sub ($sz)"
                run rm -rf "$user/.cache/$sub"
            fi
        done

        # Browser caches (Chrome, Firefox, Brave, Edge)
        for browser in google-chrome chromium firefox brave-browser microsoft-edge; do
            if [[ -d "$user/.cache/$browser" ]]; then
                sz=$(du -sh "$user/.cache/$browser" 2>/dev/null | cut -f1)
                warn "  Removing $browser cache ($sz)"
                run rm -rf "$user/.cache/$browser"
            fi
        done
    fi

    # .local/share (your 19G)
    if [[ -d "$user/.local/share" ]]; then
        local_size=$(du -sh "$user/.local/share" 2>/dev/null | cut -f1)
        log "User $un .local/share: $local_size"

        # Trash
        if [[ -d "$user/.local/share/Trash" ]]; then
            sz=$(du -sh "$user/.local/share/Trash" 2>/dev/null | cut -f1)
            warn "  Emptying Trash ($sz)"
            run rm -rf "$user/.local/share/Trash/files/*" "$user/.local/share/Trash/info/*"
        fi

        # Flatpak unused runtimes
        if [[ -d "$user/.local/share/flatpak" ]]; then
            warn "  Flatpak cleanup"
            run flatpak uninstall --unused -y 2>/dev/null || true
        fi
    fi
done

# --- 2. SYSTEM CLEANUP ---
log "=== SYSTEM CLEANUP ==="

# /var/cache (your 19G)
if [[ -d /var/cache ]]; then
    varcache=$(du -sh /var/cache 2>/dev/null | cut -f1)
    log "/var/cache: $varcache"

    # apt cache
    if [[ -d /var/cache/apt/archives ]]; then
        sz=$(du -sh /var/cache/apt/archives 2>/dev/null | cut -f1)
        warn "  Cleaning apt archives ($sz)"
        run apt-get clean 2>/dev/null || rm -rf /var/cache/apt/archives/*.deb
    fi

    # dnf/yum cache
    if command -v dnf &>/dev/null; then
        warn "  dnf cache clean"
        run dnf clean all 2>/dev/null || true
    elif command -v yum &>/dev/null; then
        warn "  yum cache clean"
        run yum clean all 2>/dev/null || true
    fi

    # pacman cache
    if command -v pacman &>/dev/null; then
        warn "  pacman cache clean"
        run pacman -Sc --noconfirm 2>/dev/null || true
    fi
fi

# /tmp (your 12G)
if [[ -d /tmp ]]; then
    tmp_size=$(du -sh /tmp 2>/dev/null | cut -f1)
    log "/tmp: $tmp_size"
    warn "  Cleaning old /tmp files (>7 days)"
    run find /tmp -type f -atime +7 -delete 2>/dev/null || true
    run find /tmp -type d -empty -delete 2>/dev/null || true
fi

# /var/log (202M)
if [[ -d /var/log ]]; then
    log_size=$(du -sh /var/log 2>/dev/null | cut -f1)
    log "/var/log: $log_size"
    warn "  Rotating and compressing old logs"
    run find /var/log -type f -name "*.log" -size +10M -exec gzip {} \; 2>/dev/null || true
    run find /var/log -type f -name "*.gz" -mtime +30 -delete 2>/dev/null || true
    run journalctl --vacuum-time=7d 2>/dev/null || true
fi

# --- 3. DOCKER CLEANUP ---
log "=== DOCKER CLEANUP ==="
if command -v docker &>/dev/null; then
    warn "  Docker system prune"
    run docker system prune -af --volumes 2>/dev/null || true

    # Remove dangling images
    dangling=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l)
    if [[ "$dangling" -gt 0 ]]; then
        warn "  Removing $dangling dangling images"
        run docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
    fi
fi

# --- 4. SNAP CLEANUP ---
if command -v snap &>/dev/null; then
    log "=== SNAP CLEANUP ==="
    warn "  Removing old snap revisions"
    run snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
        run snap remove "$snapname" --revision="$revision" 2>/dev/null || true
    done
fi

# --- 5. CORE DUMPS ---
log "=== CORE DUMPS ==="
if [[ -d /var/lib/systemd/coredump ]]; then
    core_size=$(du -sh /var/lib/systemd/coredump 2>/dev/null | cut -f1)
    warn "  Cleaning coredumps ($core_size)"
    run rm -rf /var/lib/systemd/coredump/*
fi

# --- 6. SUMMARY ---
log "=== SUMMARY ==="
echo ""
echo "Run with DRY_RUN=0 to actually execute."
echo "Current mode: $(if [[ "$DRY_RUN" == "1" ]]; then echo "DRY-RUN (no changes)"; else echo "LIVE"; fi)"
