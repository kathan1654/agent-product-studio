"""Reviewer — validates all generated files, writes CHANGELOG.md."""
from google.adk.agents import LlmAgent
from .tools.gcs_tools import read_file, write_file, list_files

reviewer_agent = LlmAgent(
    name="reviewer_agent",
    model="gemini-2.5-pro",
    description="Reviews all generated files for correctness. Max 2 cycles.",
    instruction=(
        "You are the Reviewer agent. Read every file, check correctness, fix minor issues.\n"
        "Max 2 review cycles — after cycle 2, pass with notes regardless.\n\n"
        "STEP 1: Call list_files(project_name) and read_file() on EVERY file.\n"
        "STEP 2: Check: st.set_page_config() first, st.tabs() navigation, @st.cache_data on BQ functions,\n"
        "  all imports in requirements.txt, db-dtypes included, try/except on queries,\n"
        "  Dockerfile python:3.11-slim port 8501 headless=true,\n"
        "  Cloud Build correct timeouts and image paths,\n"
        "  Terraform correct backend/provider/IAM.\n\n"
        "STEP 3: Self-fix minor issues using write_file(). Flag major issues back.\n"
        "STEP 4: ALWAYS write CHANGELOG.md using write_file() with review results.\n\n"
        "Report: REVIEW PASSED or ISSUES FOUND with specific details."
    ),
    tools=[read_file, write_file, list_files],
)
