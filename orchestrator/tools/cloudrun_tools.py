"""Cloud Run tools for listing existing services."""
import os
from google.cloud import run_v2

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gcp-app-infra-dev")
REGION = os.environ.get("GCP_REGION", "northamerica-northeast1")

def list_services() -> list[dict]:
    """List all Cloud Run services to detect naming conflicts."""
    try:
        client = run_v2.ServicesClient()
        parent = f"projects/{PROJECT_ID}/locations/{REGION}"
        services = []
        for svc in client.list_services(parent=parent):
            services.append({"name": svc.name.split("/")[-1], "url": svc.uri})
        return services if services else [{"info": "No services found"}]
    except Exception as e:
        return [{"error": str(e)}]
