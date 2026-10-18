"""Deploy the Fieldwork demo with Vertex ADC, Firestore, GCS and Cloud Run.

Requires gcloud login and project permissions. No Gemini API key is used.
python deploy_google_cloud.py --project PROJECT --region asia-southeast1
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--region", default="asia-southeast1")
    args = ap.parse_args()
    gcloud = shutil.which("gcloud") or str(Path.home() / ".local/bin/gcloud")
    env = dict(os.environ)
    env.setdefault("CLOUDSDK_PYTHON", os.sys.executable)

    def run(*command, capture=False, input_text=None):
        print("gcloud " + " ".join(command[:4]), flush=True)
        completed = subprocess.run([gcloud, *command, "--project", args.project, "--quiet"],
                                   env=env, text=True, input=input_text,
                                   stdout=subprocess.PIPE if capture else None, check=True)
        return (completed.stdout or "").strip()

    run("services", "enable", "run.googleapis.com", "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com", "aiplatform.googleapis.com", "firestore.googleapis.com",
        "storage.googleapis.com", "secretmanager.googleapis.com", "cloudresourcemanager.googleapis.com")
    number = run("projects", "describe", args.project, "--format=value(projectNumber)", capture=True)
    runtime = f"fieldwork-runtime@{args.project}.iam.gserviceaccount.com"
    accounts = run("iam", "service-accounts", "list", "--format=value(email)", capture=True).splitlines()
    if runtime not in accounts:
        run("iam", "service-accounts", "create", "fieldwork-runtime", "--display-name=Fieldwork runtime")
    for role in ("aiplatform.user", "datastore.user", "serviceusage.serviceUsageConsumer"):
        run("projects", "add-iam-policy-binding", args.project, f"--member=serviceAccount:{runtime}",
            f"--role=roles/{role}", "--condition=None", capture=True)
    build = f"{number}-compute@developer.gserviceaccount.com"
    run("projects", "add-iam-policy-binding", args.project, f"--member=serviceAccount:{build}",
        "--role=roles/run.builder", "--condition=None", capture=True)
    bucket = args.project + "-fieldwork"
    buckets = run("storage", "buckets", "list", "--format=value(name)", capture=True)
    if bucket not in buckets:
        run("storage", "buckets", "create", "gs://" + bucket, "--location=" + args.region,
            "--uniform-bucket-level-access")
    run("storage", "buckets", "add-iam-policy-binding", "gs://" + bucket,
        f"--member=serviceAccount:{runtime}", "--role=roles/storage.objectAdmin", capture=True)
    databases = run("firestore", "databases", "list", "--format=value(name)", capture=True)
    if "/databases/(default)" not in databases:
        run("firestore", "databases", "create", "--database=(default)",
            "--location=" + args.region, "--type=firestore-native")
    secret = "fieldwork-review-token"
    names = run("secrets", "list", "--format=value(name)", capture=True)
    if secret not in [n.rsplit("/", 1)[-1] for n in names.splitlines()]:
        run("secrets", "create", secret, "--replication-policy=automatic")
    local_token = ROOT / "fieldwork-ai" / ".env.review"
    if local_token.exists():
        token = local_token.read_text().strip().split("=", 1)[1]
    else:
        token = secrets.token_urlsafe(32)
        fd = os.open(local_token, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write("FW_REVIEW_TOKEN=" + token + "\n")
    run("secrets", "versions", "add", secret, "--data-file=-", input_text=token, capture=True)
    run("secrets", "add-iam-policy-binding", secret, f"--member=serviceAccount:{runtime}",
        "--role=roles/secretmanager.secretAccessor", capture=True)
    # Prototype payment state uses process-local locks. Keep one worker and one request at a time.
    run("run", "deploy", "fieldwork-api", "--source=" + str(ROOT / "fieldwork-ai"),
        "--region=" + args.region, "--service-account=" + runtime, "--memory=4Gi", "--cpu=2",
        "--concurrency=1", "--max-instances=1", "--min-instances=0", "--timeout=600",
        "--allow-unauthenticated", "--set-secrets=FW_REVIEW_TOKEN=" + secret + ":latest",
        "--set-env-vars=" + ",".join(("FW_USE_VERTEX=1", "FW_GCP_PROJECT=" + args.project,
            "FW_GCP_LOCATION=global", "FW_STORE=cloud", "FW_BUCKET=" + bucket, "FW_WORK_DIR=/tmp/fieldwork")))
    api = run("run", "services", "describe", "fieldwork-api", "--region=" + args.region,
              "--format=value(status.url)", capture=True)
    (ROOT / "fieldwork-app" / ".env.production").write_text("NEXT_PUBLIC_API_BASE=" + api + "\n")
    run("run", "deploy", "fieldwork-web", "--source=" + str(ROOT / "fieldwork-app"),
        "--region=" + args.region, "--memory=512Mi", "--max-instances=2", "--allow-unauthenticated")
    web = run("run", "services", "describe", "fieldwork-web", "--region=" + args.region,
              "--format=value(status.url)", capture=True)
    run("run", "services", "update", "fieldwork-api", "--region=" + args.region,
        "--update-env-vars=FW_CORS_ORIGINS=" + web)
    result = {"project": args.project, "region": args.region, "api": api, "web": web,
              "review": web + "/review", "payment": "simulated", "api_max_instances": 1}
    (ROOT / "fieldwork-ai/data/results/cloud-deployment.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
