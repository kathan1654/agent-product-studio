"""GCS workspace tools for reading/writing generated project files."""
import json
import os
from datetime import datetime, timezone
from google.cloud import storage

BUCKET = os.environ.get("AGENT_WORKSPACE_BUCKET", "agent-product-studio")
PREFIX = "agent-workspace"

def _client():
    return storage.Client()

def write_file(project_name: str, path: str, content: str) -> str:
    """Write a file to gs://agent-product-studio/agent-workspace/project/path."""
    try:
        blob_path = f"{PREFIX}/{project_name}/{path}"
        _client().bucket(BUCKET).blob(blob_path).upload_from_string(
            content, content_type="text/plain; charset=utf-8"
        )
        return f"Written: gs://{BUCKET}/{blob_path}"
    except Exception as e:
        return f"Error writing {path}: {e}"

def read_file(project_name: str, path: str) -> str:
    """Read a file from the project workspace in GCS."""
    try:
        blob_path = f"{PREFIX}/{project_name}/{path}"
        blob = _client().bucket(BUCKET).blob(blob_path)
        if not blob.exists():
            return f"Not found: gs://{BUCKET}/{blob_path}"
        return blob.download_as_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading {path}: {e}"

def list_files(project_name: str) -> list[str]:
    """List all files in a project workspace."""
    try:
        prefix = f"{PREFIX}/{project_name}/"
        blobs = _client().bucket(BUCKET).list_blobs(prefix=prefix)
        files = sorted([b.name[len(prefix):] for b in blobs if b.name[len(prefix):]])
        return files if files else ["(empty project)"]
    except Exception as e:
        return [f"Error: {e}"]

def list_projects() -> list[str]:
    """List all project folders in the workspace bucket."""
    try:
        prefix = f"{PREFIX}/"
        blobs = _client().list_blobs(BUCKET, prefix=prefix, delimiter="/")
        projects = []
        for page in blobs.pages:
            for p in page.prefixes:
                name = p[len(prefix):].rstrip("/")
                if name:
                    projects.append(name)
        return sorted(projects) if projects else ["(no projects yet)"]
    except Exception as e:
        return [f"Error: {e}"]

def save_requirements(project_name: str, requirements: dict) -> str:
    """Write structured requirements.json to GCS."""
    try:
        requirements["_meta"] = {
            "created": datetime.now(timezone.utc).isoformat(),
            "by": "orchestrator",
        }
        return write_file(project_name, "requirements.json", json.dumps(requirements, indent=2))
    except Exception as e:
        return f"Error writing requirements.json: {e}"

def get_pull_commands(project_name: str) -> str:
    """Generate pull and preview commands for a completed project."""
    gs_path = f"gs://{BUCKET}/{PREFIX}/{project_name}/"
    local = f"C:/GCP/{project_name}"
    return (
        f"PULL:      gcloud storage cp -r {gs_path} {local}/\n"
        f"PREVIEW:   cd {local} && pip install -r requirements.txt && streamlit run app.py\n"
        f"TERRAFORM: cd {local}/terraform && terraform init && terraform plan\n"
        f"DEPLOY:    git init && git add . && git commit -m 'feat: {project_name}' && git push origin dev\n"
        f"THEN:      Open PR dev->main, Cloud Build runs plan, merge, approve, deployed."
    )
