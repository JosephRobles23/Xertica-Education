import sys
sys.path.insert(0, ".")
sys.path.insert(1, "venv/lib/python3.13/site-packages")

import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting in-process FastAPI endpoint verification...")

# 1. Verify Root
r_root = client.get("/")
print("GET / -> Status:", r_root.status_code, "| Response:", r_root.json())
assert r_root.status_code == 200

# 2. Create a Job
r_create = client.post("/jobs/", json={"type": "test_sourcing", "payload": {}})
print("POST /jobs/ -> Status:", r_create.status_code, "| Response:", r_create.json())
assert r_create.status_code == 200
job_id = r_create.json()["id"]

# 3. Poll and verify state transitions
print("Checking initial state (should be queued)...")
r_status1 = client.get(f"/jobs/{job_id}")
print("GET /jobs/{id} -> Status:", r_status1.json()["status"], "| Progress:", r_status1.json()["progress"])
assert r_status1.json()["status"] == "queued"

print("Waiting 2.5 seconds...")
time.sleep(2.5)
print("Checking intermediate state (should be running)...")
r_status2 = client.get(f"/jobs/{job_id}")
print("GET /jobs/{id} -> Status:", r_status2.json()["status"], "| Progress:", r_status2.json()["progress"])
assert r_status2.json()["status"] == "running"

print("Waiting 4 seconds...")
time.sleep(4.0)
print("Checking final state (should be completed)...")
r_status3 = client.get(f"/jobs/{job_id}")
print("GET /jobs/{id} -> Status:", r_status3.json()["status"], "| Progress:", r_status3.json()["progress"], "| Result:", r_status3.json()["result"])
assert r_status3.json()["status"] == "completed"
assert r_status3.json()["result"] is not None

print("\nVERIFICATION SUCCESS: FastAPI successfully booted, and Job State transitions correctly polled/verified!")
