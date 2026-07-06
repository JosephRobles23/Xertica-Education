import sys
sys.path.insert(0, ".")
sys.path.insert(1, "venv/lib/python3.13/site-packages")

import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting in-process FastAPI CRUD endpoint verification...")

# 1. Verify Root
r_root = client.get("/")
print("GET / -> Status:", r_root.status_code, "| Response:", r_root.json())
assert r_root.status_code == 200

# 2. List initial paths
r_list = client.get("/learning-paths/")
print("GET /learning-paths/ -> Status:", r_list.status_code, "| Count:", len(r_list.json()))
assert r_list.status_code == 200
assert len(r_list.json()) >= 2

# 3. Create a new path
r_create = client.post("/learning-paths/", json={
    "titulo": "Nueva Ruta de Pruebas",
    "tema": "Machine Learning",
    "brief": "Una descripción detallada."
})
print("POST /learning-paths/ -> Status:", r_create.status_code, "| Response:", r_create.json())
assert r_create.status_code == 200
new_id = r_create.json()["id"]

# 4. Fetch the created path
r_get = client.get(f"/learning-paths/{new_id}")
print("GET /learning-paths/{id} -> Status:", r_get.status_code, "| Name:", r_get.json()["name"])
assert r_get.status_code == 200
assert r_get.json()["name"] == "Nueva Ruta de Pruebas"

# 5. Patch the created path
r_patch = client.patch(f"/learning-paths/{new_id}", json={
    "name": "Ruta de Pruebas Modificada",
    "status": "aprobado"
})
print("PATCH /learning-paths/{id} -> Status:", r_patch.status_code, "| Modified Name:", r_patch.json()["name"], "| Status:", r_patch.json()["status"])
assert r_patch.status_code == 200
assert r_patch.json()["name"] == "Ruta de Pruebas Modificada"
assert r_patch.json()["status"] == "aprobado"

print("\nVERIFICATION SUCCESS: Learning path CRUD endpoints verified successfully!")
