"""Test CORS preflight for PATCH and the viewer/approve flow."""
import requests

# Test CORS preflight for PATCH (browsers send this before PATCH with JSON)
headers = {
    "Origin": "http://127.0.0.1:8000",
    "Access-Control-Request-Method": "PATCH",
    "Access-Control-Request-Headers": "content-type",
}
r = requests.options("http://127.0.0.1:8000/api/applications/LEND-1E983100/approve", headers=headers)
print(f"OPTIONS /approve: {r.status_code}")
for k, v in r.headers.items():
    if k.startswith("access-control"):
        print(f"  {k}: {v}")

# Get a real application and check its data structure
r2 = requests.get("http://127.0.0.1:8000/api/applications")
apps = r2.json().get("applications", [])
for app in apps[:3]:
    print(f"\nApp {app['id']}:")
    print(f"  status: {app.get('status')}")
    print(f"  riskScore: {app.get('riskScore')}")
    print(f"  docs count: {len(app.get('documents', []))}")
    for d in app.get("documents", []):
        print(f"    - {d.get('name')} ({d.get('status')})")

print("\nDone")
