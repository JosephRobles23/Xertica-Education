import sys
sys.path.insert(0, ".")
sys.path.insert(1, "venv/lib/python3.13/site-packages")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting in-process FastAPI endpoint verification...")

# 1. Verify Root
r_root = client.get("/")
print("GET / -> Status:", r_root.status_code, "| Response:", r_root.json())
assert r_root.status_code == 200

# 2. Verify Jobs Route
r_jobs = client.get("/jobs/")
print("GET /jobs/ -> Status:", r_jobs.status_code, "| Response:", r_jobs.json())
assert r_jobs.status_code == 200

# 3. Verify Learning Paths Route
r_lp = client.get("/learning-paths/")
print("GET /learning-paths/ -> Status:", r_lp.status_code, "| Response:", r_lp.json())
assert r_lp.status_code == 200

print("\nVERIFICATION SUCCESS: FastAPI successfully booted and all routers compile/resolve without errors!")
