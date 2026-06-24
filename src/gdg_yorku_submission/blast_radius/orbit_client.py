import os
import json
import logging
from typing import Optional, Dict, Any, List
from gdg_yorku_submission.blast_radius.orbit_graph import (
    OrbitQueryResult,
    OrbitNode,
    OrbitEdge,
    execute_query,
    single_node_query,
    project_scoped_traversal
)

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
def _detect_query_kind(dsl_payload: Dict[str, Any]) -> str:
    query = dsl_payload.get("query", {})
    node = query.get("node")
    if isinstance(node, dict):
        return node.get("entity", "").lower()

    # Check relationships
    relationships = query.get("relationships", [])
    if isinstance(relationships, list) and relationships:
        rel_types = {r.get("type") for r in relationships if isinstance(r, dict) and r.get("type")}
        if "CALLS" in rel_types:
            return "calls"
        if "IMPORTS" in rel_types:
            return "imported-symbols"
        if "DEFINES" in rel_types:
            return "definitions"

    # Check nodes
    nodes = query.get("nodes", [])
    if isinstance(nodes, list) and nodes:
        first_node = nodes[0]
        if isinstance(first_node, dict):
            entity = first_node.get("entity", "")
            if entity == "Definition":
                return "definitions"
            if entity == "ImportedSymbol":
                return "imported-symbols"
            if entity == "Vulnerability":
                return "vulns"
            if entity == "Pipeline":
                return "pipelines"
            if entity == "MergeRequest":
                return "merge-requests"
            if entity:
                return entity.lower()

    return "unknown"


class OrbitClient:
    """
    Client for querying the GitLab Orbit Knowledge Graph API directly.
    """
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        project_path: Optional[str] = None,
        use_fake: Optional[bool] = None,
        timeout: float = 5.0,
        fake_results: Optional[Dict[str, OrbitQueryResult]] = None
    ) -> None:
        self.api_url = api_url or os.getenv("ORBIT_API_URL")
        self.api_token = api_token or os.getenv("ORBIT_API_TOKEN")
        self.project_path = project_path or os.getenv("ORBIT_PROJECT_PATH")
        self.timeout = timeout

        if use_fake is None:
            self.use_fake = os.getenv("USE_FAKE_ORBIT", "false").lower() == "true"
        else:
            self.use_fake = use_fake

        self.fake_results = fake_results or {}

    def is_configured(self) -> bool:
        """Returns True if the client is fully configured to reach a live endpoint, or running in fake mode."""
        if self.use_fake:
            return True
        return bool(self.api_url and self.api_token and self.project_path)

    def query(self, dsl_payload: Dict[str, Any]) -> OrbitQueryResult:
        """
        POSTs a graph_query DSL payload to {base_url}/query and returns the parsed result.
        """
        if not self.is_configured():
            raise RuntimeError("OrbitClient queried but is unconfigured.")

        if self.use_fake:
            kind = _detect_query_kind(dsl_payload)
            if kind not in self.fake_results:
                if kind in ("project", "Project"):
                    return OrbitQueryResult(row_count=1, nodes=[OrbitNode(type="Project", id="dummy-id")])
                return OrbitQueryResult()
            return self.fake_results[kind]

        from gdg_yorku_submission.blast_radius.orbit_graph import execute_query
        return execute_query(self.api_url, self.api_token, dsl_payload, timeout=self.timeout)

    def health_check(self) -> bool:
        """Cheap probe to verify connectivity and project presence in Orbit."""
        if not self.is_configured():
            return False
        try:
            if self.use_fake:
                return True
            if not self.project_path:
                return False
            payload = single_node_query(
                "Project",
                "p",
                filters={"full_path": {"op": "eq", "value": self.project_path}},
                limit=1
            )
            self.query(payload)
            return True
        except Exception as e:
            logger.warning(f"Orbit connectivity check failed: {e}")
            return False

    def fetch_definitions(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = {
            "query": {
                "query_type": "traversal",
                "nodes": [
                    {"id": "d", "entity": "Definition", "columns": ["id", "name", "fqn", "file_path", "start_line", "end_line", "definition_type"]},
                    {"id": "f", "entity": "File", "columns": ["id", "path"]},
                    {"id": "b", "entity": "Branch", "columns": ["id"]},
                    {
                        "id": "p",
                        "entity": "Project",
                        "columns": ["id", "full_path"],
                        "filters": {
                            "full_path": {"op": "eq", "value": self.project_path}
                        }
                    }
                ],
                "relationships": [
                    {"type": "DEFINES", "from": "f", "to": "d", "direction": "outgoing"},
                    {"type": "ON_BRANCH", "from": "f", "to": "b", "direction": "outgoing"},
                    {"type": "IN_PROJECT", "from": "b", "to": "p", "direction": "outgoing"}
                ],
                "limit": limit
            },
            "response_format": "raw"
        }
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Definitions query reached the limit of {limit} rows and was truncated.")
        return res

    def fetch_calls(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = {
            "query": {
                "query_type": "traversal",
                "nodes": [
                    {"id": "src", "entity": "Definition", "columns": ["id", "name", "fqn", "file_path", "start_line", "end_line", "definition_type"]},
                    {"id": "dst", "entity": "Definition", "columns": ["id", "name", "fqn", "file_path", "start_line", "end_line", "definition_type"]},
                    {"id": "f", "entity": "File", "columns": ["id", "path"]},
                    {"id": "b", "entity": "Branch", "columns": ["id"]},
                    {
                        "id": "p",
                        "entity": "Project",
                        "columns": ["id", "full_path"],
                        "filters": {
                            "full_path": {"op": "eq", "value": self.project_path}
                        }
                    }
                ],
                "relationships": [
                    {"type": "CALLS", "from": "src", "to": "dst", "direction": "outgoing"},
                    {"type": "DEFINES", "from": "f", "to": "src", "direction": "outgoing"},
                    {"type": "ON_BRANCH", "from": "f", "to": "b", "direction": "outgoing"},
                    {"type": "IN_PROJECT", "from": "b", "to": "p", "direction": "outgoing"}
                ],
                "limit": limit
            },
            "response_format": "raw"
        }
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Calls query reached the limit of {limit} rows and was truncated.")
        return res

    def fetch_imports(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = {
            "query": {
                "query_type": "traversal",
                "nodes": [
                    {"id": "i", "entity": "ImportedSymbol", "columns": "*"},
                    {"id": "f", "entity": "File", "columns": ["id", "path"]},
                    {"id": "b", "entity": "Branch", "columns": ["id"]},
                    {
                        "id": "p",
                        "entity": "Project",
                        "columns": ["id", "full_path"],
                        "filters": {
                            "full_path": {"op": "eq", "value": self.project_path}
                        }
                    }
                ],
                "relationships": [
                    {"type": "IMPORTS", "from": "f", "to": "i", "direction": "outgoing"},
                    {"type": "ON_BRANCH", "from": "f", "to": "b", "direction": "outgoing"},
                    {"type": "IN_PROJECT", "from": "b", "to": "p", "direction": "outgoing"}
                ],
                "limit": limit
            },
            "response_format": "raw"
        }
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Imports query reached the limit of {limit} rows and was truncated.")
        return res

    def fetch_vulnerabilities(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = project_scoped_traversal("Vulnerability", "v", self.project_path, limit=limit)
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Vulnerabilities query reached the limit of {limit} rows and was truncated.")
        return res

    def fetch_pipelines(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = project_scoped_traversal("Pipeline", "pl", self.project_path, limit=limit)
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Pipelines query reached the limit of {limit} rows and was truncated.")
        return res

    def fetch_merge_requests(self, limit: int = 500) -> OrbitQueryResult:
        if not self.project_path:
            raise RuntimeError("ORBIT_PROJECT_PATH is not set.")
        payload = project_scoped_traversal("MergeRequest", "mr", self.project_path, limit=limit)
        res = self.query(payload)
        if res.row_count >= limit:
            logger.warning(f"Merge requests query reached the limit of {limit} rows and was truncated.")
        return res
