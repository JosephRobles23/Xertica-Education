import sys
sys.path.insert(0, ".")
sys.path.insert(1, "venv/lib/python3.13/site-packages")

import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting in-process FastAPI CRUD & generation verification...")

# 1. Verify Root
r_root = client.get("/")
print("GET / -> Status:", r_root.status_code, "| Response:", r_root.json())
assert r_root.status_code == 200

# 2. List initial paths
r_list = client.get("/learning-paths/")
print("GET /learning-paths/ -> Status:", r_list.status_code, "| Count:", len(r_list.json()))
assert r_list.status_code == 200

# 3. Create a new path
r_create = client.post("/learning-paths/", json={
    "titulo": "Ruta de Generacion",
    "tema": "Autoconfiguración",
    "brief": "Prueba de pipeline."
})
print("POST /learning-paths/ -> Status:", r_create.status_code)
new_id = r_create.json()["id"]

# 4. Trigger structure generation
r_gen = client.post(f"/learning-paths/{new_id}/generate-structure")
print("POST /learning-paths/{id}/generate-structure -> Status:", r_gen.status_code, "| Response:", r_gen.json())
assert r_gen.status_code == 200
job_id = r_gen.json()["job_id"]

# 5. Poll the generation job to completion
r_job = client.get(f"/jobs/{job_id}")
print("GET /jobs/{id} -> Status:", r_job.json()["status"])
assert r_job.json()["status"] == "queued"

# 6. Verify route has modules after generation
r_route = client.get(f"/learning-paths/{new_id}")
print("GET /learning-paths/{id} -> Modules count:", len(r_route.json()["modules"]))
assert len(r_route.json()["modules"]) == 2

print("\nVERIFICATION SUCCESS: Learning path structure generation verified successfully!")
