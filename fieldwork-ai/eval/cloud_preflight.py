"""Read-only deployment permission and service checks using existing ADC."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork import config, gemini
import google.auth
from google.auth.transport.requests import AuthorizedSession

project = config.GCP_PROJECT
if not project:
    raise SystemExit("Set FW_GCP_PROJECT")
credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
session = AuthorizedSession(credentials)
permissions = ["run.services.create", "run.services.update", "run.services.get",
               "cloudbuild.builds.create", "artifactregistry.repositories.create",
               "serviceusage.services.enable", "storage.buckets.create", "datastore.databases.create"]
response = session.post(f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}:testIamPermissions",
                        json={"permissions": permissions}, timeout=30)
result = {"project": project, "permission_check_http": response.status_code}
if response.ok:
    allowed = response.json().get("permissions", [])
    result.update(allowed_permissions=allowed, missing_permissions=[p for p in permissions if p not in allowed])
else:
    result["permission_error"] = response.json().get("error", {}).get("message", "Request failed")
result["services"] = {}
for service in ("run", "cloudbuild", "artifactregistry", "aiplatform", "firestore", "storage"):
    r = session.get(f"https://serviceusage.googleapis.com/v1/projects/{project}/services/{service}.googleapis.com", timeout=30)
    result["services"][service] = {"http": r.status_code, "state": r.json().get("state")}
result["resource_access"] = {}
for name, url in {
    "cloud_run": f"https://run.googleapis.com/v2/projects/{project}/locations/asia-southeast1/services",
    "firestore": f"https://firestore.googleapis.com/v1/projects/{project}/databases",
    "buckets": f"https://storage.googleapis.com/storage/v1/b?project={project}",
}.items():
    r = session.get(url, timeout=30)
    body = r.json()
    result["resource_access"][name] = {"http": r.status_code}
    if r.ok:
        result["resource_access"][name]["names"] = [x.get("name") for x in body.get("services", body.get("databases", body.get("items", [])))]
    else:
        result["resource_access"][name]["error"] = body.get("error", {}).get("message")
out = config.ROOT / "data" / "results" / "cloud-preflight.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
