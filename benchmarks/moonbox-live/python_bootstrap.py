import sys, os
sys.path.insert(0, "/mnt/agents/output/.pip")
os.environ["PYTHONPATH"] = "/mnt/agents/output/.pip:" + os.environ.get("PYTHONPATH", "")
print("§BOOTSTRAP§ PYTHONPATH set")
