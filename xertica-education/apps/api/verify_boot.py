import sys
sys.path.insert(0, ".")
sys.path.insert(1, "venv/lib/python3.13/site-packages")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting in-process FastAPI CRUD & sourcing approve verification...")

# 1. Verify Root
r_root = client.get("/")
print("GET / -> Status:", r_root.status_code)
assert r_root.status_code == 200

# 2. Create a new path
r_create = client.post("/learning-paths/", json={
    "titulo": "Ruta de Sourcing",
    "tema": "Sourcing",
    "brief": "Prueba de sourcing."
})
new_id = r_create.json()["id"]

# 3. Sourcing approve the path
r_app = client.post(f"/learning-paths/{new_id}/sourcing/approve")
print("POST /learning-paths/{id}/sourcing/approve -> Status:", r_app.status_code, "| New Status:", r_app.json()["status"])
assert r_app.status_code == 200
assert r_app.json()["status"] == "generado"

print("\nVERIFICATION SUCCESS: Learning path sourcing approval verified successfully!")
