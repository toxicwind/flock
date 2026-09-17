#!/usr/bin/env python3
import os, sys, subprocess, time, traceback, signal

LOG_DIR = '/mnt/agents/output/.bg_logs'
STATE_DIR = '/mnt/agents/output/.bg_state'

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

def log(msg, level='INFO'):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = '[' + ts + '] [' + level + '] ' + msg
    print(line, flush=True)
    try:
        with open(LOG_DIR + '/autohook_v5.log', 'a') as f:
            f.write(line + '\n')
    except:
        pass

def debug(msg): log(msg, 'DEBUG')
def error(msg): log(msg, 'ERROR')

def kill_lock_holder(lock_path):
    """Find and kill the process holding the git lock."""
    try:
        # Try lsof first
        r = subprocess.run(['lsof', lock_path], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            for line in r.stdout.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        os.kill(pid, signal.SIGKILL)
                        debug('KILLED_LOCK_HOLDER: pid=' + str(pid) + ' for ' + lock_path)
                    except:
                        pass
    except:
        pass
    
    # Also try fuser
    try:
        subprocess.run(['fuser', '-k', lock_path], capture_output=True, timeout=3)
    except:
        pass
    
    # Finally remove the lock
    try:
        os.remove(lock_path)
        debug('LOCK_REMOVED: ' + lock_path)
        return True
    except Exception as e:
        debug('LOCK_REMOVE_FAIL: ' + str(e))
        return False

def fix_git_lock(repo_path):
    """Aggressively fix any git lock in the repo."""
    lock = os.path.join(repo_path, '.git', 'index.lock')
    if os.path.exists(lock):
        debug('LOCK_FOUND: ' + lock)
        return kill_lock_holder(lock)
    return True

def shell(cmd, cwd=None, timeout=10):
    debug('SHELL: ' + cmd[:200])
    t0 = time.time()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        dt = time.time() - t0
        debug('SHELL_DONE: rc=' + str(r.returncode) + ' dt=' + str(round(dt,2)) + 's')
        if r.returncode != 0 and r.stderr:
            debug('SHELL_ERR: ' + r.stderr[:500])
        return r.returncode == 0, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        error('SHELL_TIMEOUT: ' + cmd[:200])
        return False, '', 'TIMEOUT'
    except Exception as e:
        error('SHELL_EXC: ' + str(e))
        return False, '', str(e)

def git_safe(repo_path, args, timeout=15):
    """Run git command with automatic lock fixing."""
    # Fix lock BEFORE running
    fix_git_lock(repo_path)
    
    cmd = 'cd ' + repo_path + ' && git ' + args
    ok, out, err = shell(cmd, timeout=timeout)
    
    # If failed due to lock, fix and retry once
    if not ok and 'index.lock' in err:
        debug('RETRY_AFTER_LOCK_FIX: ' + repo_path)
        fix_git_lock(repo_path)
        ok, out, err = shell(cmd, timeout=timeout)
    
    return ok, out, err

def git_commit_repo(repo_path, msg):
    if not os.path.isdir(repo_path):
        debug('SKIP: not a dir: ' + repo_path)
        return False
    
    ok, out, err = git_safe(repo_path, 'add -A', timeout=10)
    if not ok:
        debug('GIT_ADD_FAIL: ' + err[:200])
    
    ok, out, err = git_safe(repo_path, 'commit -m "' + msg + '"', timeout=10)
    if ok:
        debug('GIT_COMMIT_OK: ' + repo_path)
        return True
    elif 'nothing to commit' in err.lower() or 'nothing to commit' in out.lower():
        debug('GIT_CLEAN: ' + repo_path)
        return True
    else:
        debug('GIT_COMMIT_FAIL: ' + err[:200])
        return False

def cycle():
    debug('=== CYCLE_START ===')
    
    repos = [
        ('/mnt/agents/output/effusion-labs', 'auto: effusion-labs'),
        ('/mnt/agents/output/envd-project', 'auto: envd-project'),
        ('/mnt/agents/output/repo_kimi_team_recon', 'auto: recon'),
        ('/mnt/agents/output/triangle-access', 'auto: triangle-access'),
        ('/mnt/agents/output/toxicwind-repos', 'auto: toxicwind-repos'),
    ]
    
    committed = 0
    for path, msg in repos:
        if git_commit_repo(path, msg):
            committed += 1
    
    debug('CYCLE_DONE: committed=' + str(committed) + '/' + str(len(repos)))
    return committed

def main():
    log('AUTOHOOK_v5_STARTED')
    while True:
        try:
            cycle()
        except Exception as e:
            error('CYCLE_CRASH: ' + str(e))
            traceback.print_exc()
        time.sleep(30)

if __name__ == '__main__':
    main()
