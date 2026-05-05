"""BigQuery tools for schema discovery and data sampling."""
import os
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gcp-app-infra-dev")

def _client():
    return bigquery.Client(project=PROJECT_ID)

def list_tables() -> list[str]:
    """List all tables in policing_raw and policing_analytics datasets."""
    client = _client()
    tables = []
    for ds in ["policing_raw", "policing_analytics"]:
        try:
            for t in client.list_tables(client.dataset(ds, project=PROJECT_ID)):
                tables.append(f"{PROJECT_ID}.{ds}.{t.table_id}")
        except Exception as e:
            tables.append(f"Error listing {ds}: {e}")
    return tables if tables else ["No tables found"]

def get_schema(table_id: str) -> list[dict]:
    """Get column names and types for a BQ table. Use fully qualified name."""
    try:
        table = _client().get_table(table_id)
        return [{"name": f.name, "type": f.field_type, "mode": f.mode} for f in table.schema]
    except Exception as e:
        return [{"error": str(e)}]

def run_query(sql: str) -> list[dict]:
    """Run a read-only BQ query. Always use LIMIT."""
    try:
        rows = [dict(r) for r in _client().query(sql).result()]
        return rows if rows else [{"info": "0 rows returned"}]
    except Exception as e:
        return [{"error": str(e)}]
