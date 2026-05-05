"""Infra — writes Terraform and Cloud Build files to GCS."""
from google.adk.agents import LlmAgent
from .tools.gcs_tools import read_file, write_file, list_files
from .tools.cloudrun_tools import list_services

infra_agent = LlmAgent(
    name="infra_agent",
    model="gemini-2.5-pro",
    description="Writes Terraform and CI/CD pipeline files to GCS.",
    instruction=(
        "You are the Infra agent. You write Terraform configs and Cloud Build YAMLs.\n"
        "You NEVER run any commands. Write files only.\n\n"
        "STEP 1: Read requirements.json and GEMINI.md using read_file().\n"
        "STEP 2: Call list_services() to confirm no naming conflicts.\n"
        "STEP 3: Write ALL files using write_file():\n"
        "  terraform/main.tf — backend gcs bucket=gcp-app-infra-dev-tfstate, provider google ~> 5.45.2\n"
        "  terraform/variables.tf — app_project_id, cicd_project_id, region, service_name, image_tag\n"
        "  terraform/outputs.tf — app_url, service_name, image_path\n"
        "  terraform/cloudrun.tf — google_cloud_run_v2_service, port 8501, min 0, max 3\n"
        "  terraform/iam.tf — allUsers->roles/run.invoker, cloudbuild-deployer->roles/run.developer\n"
        "  cloudbuild-plan.yaml — terraform init+validate+plan only, E2_HIGHCPU_8, 600s\n"
        "  cloudbuild-apply.yaml — terraform+docker build+push+deploy, E2_HIGHCPU_8, 1200s\n\n"
        "Key values:\n"
        "- Region: northamerica-northeast1\n"
        "- App project: gcp-app-infra-dev\n"
        "- CI/CD project: gcp-cicd-infra-auth\n"
        "- Deployer SA: cloudbuild-deployer@gcp-cicd-infra-auth.iam.gserviceaccount.com\n\n"
        "NEVER write app code. NEVER run terraform commands.\n"
        "Report completion with list of all files written."
    ),
    tools=[read_file, write_file, list_files, list_services],
)
