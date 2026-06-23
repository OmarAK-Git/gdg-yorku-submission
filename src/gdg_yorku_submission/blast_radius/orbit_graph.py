"""
Grounded Orbit Knowledge Graph query/response primitives.

Built strictly against the live captures in .orbit-captures/ (schema.json,
dsl.json = graph_query DSL v2.9.1, project-query.json, project-result.json).

Transport-agnostic on purpose: these helpers build the request payload and
parse the response envelope. The actual HTTP call lives in OrbitClient, so the
query/mapping logic can be unit-tested offline against recorded fixtures.

Pending real captures (do NOT guess until seen):
  - Node property names for Vulnerability / Pipeline / MergeRequest (the
    OrbitImpactContext field mapping) -> awaiting vulns/pipelines/merge-requests captures.
  - result.edges[] item shape -> awaiting a non-empty edges sample / get_response_format.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OrbitQueryError(RuntimeError):
    """
    Raised when Orbit returns an error envelope (e.g. compile_error) or the HTTP
    request fails. Callers are expected to catch this and degrade gracefully
    (per the integration contract: partial/empty results, never crash the run).
    """


class OrbitNode(BaseModel):
    """
    A row from result.nodes[]. `type` and `id` are always present (mandatory
    columns the DSL injects for redaction); all other columns are
    entity/column-selection dependent and kept verbatim in `properties`.
    """
    type: str
    id: str
    properties: Dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)


class OrbitEdge(BaseModel):
    """
    A relationship row from result.edges[]. Shape confirmed from the live
    imported-symbols capture: {"from","from_id","to","to_id","type"}.
    """
    type: str
    from_type: Optional[str] = None
    from_id: Optional[str] = None
    to_type: Optional[str] = None
    to_id: Optional[str] = None


class OrbitQueryResult(BaseModel):
    """Parsed `query_graph` response envelope (response_format="raw")."""
    query_type: str = "traversal"
    row_count: int = 0
    format_version: Optional[str] = None
    nodes: List[OrbitNode] = Field(default_factory=list)
    edges: List[OrbitEdge] = Field(default_factory=list)

    def nodes_of_type(self, entity: str) -> List[OrbitNode]:
        return [n for n in self.nodes if n.type == entity]

    def edges_of_type(self, rel: str) -> List[OrbitEdge]:
        return [e for e in self.edges if e.type == rel]


def _to_node(raw_node: Dict[str, Any]) -> OrbitNode:
    d = dict(raw_node)
    ntype = d.pop("type", None)
    nid = d.pop("id", None)
    return OrbitNode(type=str(ntype), id=str(nid), properties=d)


def _str_or_none(v: Any) -> Optional[str]:
    return None if v is None else str(v)


def _to_edge(raw_edge: Dict[str, Any]) -> OrbitEdge:
    return OrbitEdge(
        type=str(raw_edge.get("type")),
        from_type=raw_edge.get("from"),
        from_id=_str_or_none(raw_edge.get("from_id")),
        to_type=raw_edge.get("to"),
        to_id=_str_or_none(raw_edge.get("to_id")),
    )


def parse_orbit_response(raw: Dict[str, Any]) -> OrbitQueryResult:
    """
    Parses the Orbit `query_graph` envelope:
      {"result": {"format_version", "query_type", "nodes":[...], "edges":[...]},
       "query_type": "...", "row_count": N}
    Lenient by design so a partial/absent relationship degrades to empty rather
    than raising (graceful degradation per the integration contract).
    """
    if not isinstance(raw, dict):
        return OrbitQueryResult()
    result = raw.get("result") or {}
    nodes = [_to_node(n) for n in result.get("nodes", []) if isinstance(n, dict)]
    edges = [_to_edge(e) for e in result.get("edges", []) if isinstance(e, dict)]
    return OrbitQueryResult(
        query_type=result.get("query_type") or raw.get("query_type") or "traversal",
        row_count=raw.get("row_count", result.get("row_count", len(nodes))),
        format_version=result.get("format_version"),
        nodes=nodes,
        edges=edges,
    )


# --- Query builders (compile to the graph_query JSON DSL, v2.9.1) -------------

def single_node_query(
    entity: str,
    var: str,
    *,
    columns: Union[str, List[str]] = "*",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 30,
    response_format: str = "raw",
) -> Dict[str, Any]:
    """
    Single-node traversal (table scan), e.g. probe whether an entity domain is
    indexed. Mirrors .orbit-captures/project-query.json exactly.
    """
    node: Dict[str, Any] = {"id": var, "entity": entity, "columns": columns}
    if filters:
        node["filters"] = filters
    return {
        "query": {"query_type": "traversal", "node": node, "limit": limit},
        "response_format": response_format,
    }


def project_scoped_traversal(
    entity: str,
    var: str,
    project_full_path: str,
    *,
    edge_type: str = "IN_PROJECT",
    columns: Union[str, List[str]] = "*",
    limit: int = 50,
    project_var: str = "p",
    response_format: str = "raw",
) -> Dict[str, Any]:
    """
    Two-node traversal returning `entity` rows that are IN_PROJECT the project
    identified by full_path. Used for Vulnerability / Pipeline / MergeRequest
    impact context. `entity -IN_PROJECT-> Project` is an outgoing edge per
    schema.json, so direction is "outgoing" from `var` to the project node.
    """
    return {
        "query": {
            "query_type": "traversal",
            "nodes": [
                {"id": var, "entity": entity, "columns": columns},
                {
                    "id": project_var,
                    "entity": "Project",
                    "columns": ["id", "full_path"],
                    "filters": {"full_path": {"op": "eq", "value": project_full_path}},
                },
            ],
            "relationships": [
                {"type": edge_type, "from": var, "to": project_var, "direction": "outgoing"}
            ],
            "limit": limit,
        },
        "response_format": response_format,
    }


# --- Transport (confirmed against the live POST /api/v4/orbit/query) ----------
# Verified end-to-end: Bearer PAT auth, JSON body {"query":...,"response_format":"raw"},
# success envelope {"result":{...}}, error envelopes {"code","message"} / {"error"}.

def _interpret(raw: Any) -> OrbitQueryResult:
    if isinstance(raw, dict) and "result" in raw:
        return parse_orbit_response(raw)
    msg = None
    if isinstance(raw, dict):
        msg = raw.get("message") or raw.get("error") or raw.get("code")
    raise OrbitQueryError(msg or f"Unexpected Orbit response: {raw!r}")


def execute_query(
    base_url: str,
    token: str,
    dsl_payload: Dict[str, Any],
    *,
    timeout: float = 10.0,
) -> OrbitQueryResult:
    """
    POSTs a graph_query DSL payload to {base_url}/query and returns the parsed
    result. Raises OrbitQueryError on an Orbit error envelope or transport
    failure (GitLab returns JSON error bodies even on 4xx). Body is encoded as
    UTF-8 with no BOM (the BOM is exactly what GitLab rejected as "Invalid JSON").
    """
    url = base_url.rstrip("/") + "/query"
    body = json.dumps(dsl_payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            raw = json.loads(e.read().decode("utf-8"))
        except Exception:
            raise OrbitQueryError(f"Orbit HTTP {e.code}") from e
    except Exception as e:
        raise OrbitQueryError(str(e)) from e
    return _interpret(raw)
