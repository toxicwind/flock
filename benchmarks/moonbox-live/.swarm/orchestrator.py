#!/usr/bin/env python3
# SWARM ORCHESTRATOR v1.0
# Coordinates all auxiliary agents with priority scheduling
# Zero-race: file-based state machine with atomic renames

import os, sys, json, time, subprocess, signal, threading
from collections import deque

STATE_DIR = "/mnt/agents/output/.swarm/state"
LOG_DIR = "/mnt/agents/output/.swarm/logs"
AGENTS_DIR = "/mnt/agents/output/.agents"

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

class Agent:
    def __init__(self, name, script, priority=5, restart=True):
        self.name = name
        self.script = script
        self.priority = priority
        self.restart = restart
        self.pid = None
        self.last_heartbeat = 0
        self.status = "stopped"
        self.restarts = 0

    def start(self):
        log = os.path.join(LOG_DIR, f"{self.name}.log")
        with open(log, "a") as f:
            proc = subprocess.Popen(
                ["python3", self.script],
                stdout=f, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self.pid = proc.pid
        self.status = "running"
        self.last_heartbeat = time.time()
        return proc.pid

    def check(self):
        if self.pid is None:
            return False
        try:
            os.kill(self.pid, 0)
            self.last_heartbeat = time.time()
            return True
        except ProcessLookupError:
            self.status = "crashed"
            self.pid = None
            return False

    def stop(self):
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(1)
                os.kill(self.pid, signal.SIGKILL)
            except:
                pass
            self.pid = None
            self.status = "stopped"

class SwarmOrchestrator:
    def __init__(self):
        self.agents = {}
        self.running = True
        self._lock = threading.Lock()

    def register(self, name, script, priority=5, restart=True):
        self.agents[name] = Agent(name, script, priority, restart)

    def start_all(self):
        for name, agent in sorted(self.agents.items(), key=lambda x: x[1].priority):
            agent.start()
            print(f"[SWARM] Started {name} (PID {agent.pid}, priority {agent.priority})")
            time.sleep(0.5)

    def monitor(self):
        while self.running:
            for name, agent in self.agents.items():
                if not agent.check():
                    if agent.restart and agent.restarts < 10:
                        agent.restarts += 1
                        agent.start()
                        print(f"[SWARM] Restarted {name} (attempt {agent.restarts})")

            # Write state atomically
            state = {
                "timestamp": time.time(),
                "agents": {
                    name: {
                        "pid": a.pid,
                        "status": a.status,
                        "restarts": a.restarts,
                        "last_heartbeat": a.last_heartbeat,
                    }
                    for name, a in self.agents.items()
                }
            }
            tmp = os.path.join(STATE_DIR, "swarm.state.tmp")
            final = os.path.join(STATE_DIR, "swarm.state.json")
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2)
            os.rename(tmp, final)

            time.sleep(5)

    def stop_all(self):
        self.running = False
        for agent in self.agents.values():
            agent.stop()

def main():
    orch = SwarmOrchestrator()

    # Register all agents
    orch.register("kernel_tracer", os.path.join(AGENTS_DIR, "kernel_tracer.py"), priority=1)
    orch.register("build_orchestrator", os.path.join(AGENTS_DIR, "build_orchestrator.py"), priority=2)
    orch.register("osint_harvester", os.path.join(AGENTS_DIR, "osint_harvester.py"), priority=3)
    orch.register("hf_sampler", os.path.join(AGENTS_DIR, "hf_sampler.py"), priority=4)
    orch.register("simd_hasher", os.path.join(AGENTS_DIR, "simd_hasher.py"), priority=5)
    orch.register("rate_limiter", os.path.join(AGENTS_DIR, "rate_limiter.py"), priority=6)

    orch.start_all()

    try:
        orch.monitor()
    except KeyboardInterrupt:
        orch.stop_all()

if __name__ == "__main__":
    main()
