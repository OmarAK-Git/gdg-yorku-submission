"""
Blast-radius computation over the Orbit code graph.

Pure functions over parsed OrbitQueryResult data (Definitions + CALLS edges) —
no transport, no I/O — so they unit-test against recorded captures. Grounded in
.orbit-captures: Definition nodes carry name/fqn/file_path/start_line/end_line/
definition_type; CALLS edges are Definition->Definition (caller -> callee), so the
*reverse* of CALLS answers "who depends on this symbol" = its blast radius.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set
from gdg_yorku_submission.blast_radius.orbit_graph import OrbitQueryResult


def _to_int(v, default: int = 1) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@dataclass
class DefInfo:
    id: str
    name: str
    fqn: str
    file_path: str
    start_line: int
    end_line: int
    definition_type: str


@dataclass
class ImpactGraph:
    defs: Dict[str, DefInfo] = field(default_factory=dict)
    # callee_id -> caller_ids  (reverse CALLS = "who depends on me")
    callers: Dict[str, Set[str]] = field(default_factory=dict)
    # caller_id -> callee_ids  (forward CALLS = "what I depend on")
    callees: Dict[str, Set[str]] = field(default_factory=dict)

    def dependents(self, def_id: str, max_hops: int = 3) -> Set[str]:
        """Transitive set of definitions that (in)directly call `def_id`."""
        seen: Set[str] = set()
        frontier = {def_id}
        for _ in range(max(1, max_hops)):
            nxt: Set[str] = set()
            for cur in frontier:
                for caller in self.callers.get(cur, ()):
                    if caller != def_id and caller not in seen:
                        seen.add(caller)
                        nxt.add(caller)
            if not nxt:
                break
            frontier = nxt
        return seen


def _ingest_defs(result: OrbitQueryResult, graph: ImpactGraph) -> None:
    for n in result.nodes_of_type("Definition"):
        if n.id in graph.defs:
            continue
        graph.defs[n.id] = DefInfo(
            id=n.id,
            name=n.get("name", "") or "",
            fqn=n.get("fqn", "") or "",
            file_path=n.get("file_path", "") or "",
            start_line=_to_int(n.get("start_line")),
            end_line=_to_int(n.get("end_line")),
            definition_type=n.get("definition_type", "") or "",
        )


def build_impact_graph(definitions: OrbitQueryResult, calls: OrbitQueryResult) -> ImpactGraph:
    """Builds the caller/callee adjacency from a Definitions result and a CALLS result."""
    graph = ImpactGraph()
    _ingest_defs(definitions, graph)
    _ingest_defs(calls, graph)  # CALLS result also carries Definition rows

    for e in calls.edges_of_type("CALLS"):
        if not e.from_id or not e.to_id or e.from_id == e.to_id:
            continue  # drop self-recursion: not a blast relationship
        graph.callees.setdefault(e.from_id, set()).add(e.to_id)
        graph.callers.setdefault(e.to_id, set()).add(e.from_id)
    return graph


@dataclass
class BlastSummary:
    definition: DefInfo
    dependent_ids: Set[str]
    dependent_files: Set[str]


def summarize_blast(graph: ImpactGraph, max_hops: int = 3, min_dependents: int = 1) -> List[BlastSummary]:
    """
    One BlastSummary per definition that has >= min_dependents transitive callers,
    ordered deterministically (largest blast first, then fqn, then id).
    """
    out: List[BlastSummary] = []
    for did, info in graph.defs.items():
        deps = graph.dependents(did, max_hops)
        if len(deps) < min_dependents:
            continue
        files = {
            graph.defs[d].file_path
            for d in deps
            if d in graph.defs and graph.defs[d].file_path
        }
        out.append(BlastSummary(definition=info, dependent_ids=deps, dependent_files=files))
    out.sort(key=lambda s: (-len(s.dependent_ids), s.definition.fqn, s.definition.id))
    return out
