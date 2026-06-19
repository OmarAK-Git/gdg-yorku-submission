import uuid
import abc
import copy
from typing import List, Dict, Any, Callable
from gdg_yorku_submission.schemas import (
    ReviewFinding,
    Perspective,
    ReviewReport,
    PerspectiveStatus,
    GateStatus,
    AccountingLedger,
    ReportFinding,
    GateFinding
)
from gdg_yorku_submission.finding_ids import finalize_finding_ids
from gdg_yorku_submission.severity import is_at_or_above_floor

class Orchestrator(abc.ABC):
    def __init__(self) -> None:
        self.run_id = None

    @abc.abstractmethod
    def _get_state(self) -> Dict[str, Any]:
        """Returns the dictionary containing the state for this run."""
        pass

    @abc.abstractmethod
    def _save_state(self, state: Dict[str, Any]) -> None:
        """Saves/persists the dictionary containing the state for this run."""
        pass

    def start_run(self) -> str:
        """Starts a new review run, initializes state, and returns a run_id."""
        self.run_id = str(uuid.uuid4())
        from gdg_yorku_submission.preflight.redaction import RedactionContext
        redaction_ctx = RedactionContext()
        state = {
            "run_id": self.run_id,
            "findings": [],
            "perspective_statuses": {},
            "gate_status": GateStatus(status="complete", reason=None, finding_ids=[]),
            "secret_scan_summary": [],
            "corpus_summary": {"file_count": 0, "total_bytes": 0},
            "finalized": False,
            "redaction_context": redaction_ctx,
            "corpus": {},
        }
        self._save_state(state)
        return self.run_id

    def get_redaction_context(self) -> Any:
        """Returns the run-specific RedactionContext."""
        state = self._get_state()
        return state.get("redaction_context")

    def set_corpus(self, corpus: Dict[str, Any]) -> None:
        """Saves the corpus dict in the run state."""
        state = self._get_state()
        state["corpus"] = copy.deepcopy(corpus)
        self._save_state(state)

    def get_corpus(self) -> Dict[str, Any]:
        """Returns a deep copy of the corpus dict from the run state."""
        state = self._get_state()
        return copy.deepcopy(state.get("corpus", {}))

    def set_corpus_summary(self, summary: Dict[str, Any]) -> None:
        """Sets the corpus summary for the run."""
        state = self._get_state()
        state["corpus_summary"] = summary
        self._save_state(state)

    def run_secret_gate(self, gate_findings: List[GateFinding]) -> None:
        """Sets the preflight gate findings and updates gate_status and secret_scan_summary."""
        state = self._get_state()
        if state["finalized"]:
            raise RuntimeError("Cannot write gate findings after ID finalization.")
            
        state["secret_scan_summary"] = copy.deepcopy(gate_findings)
        state["gate_status"] = GateStatus(
            status="complete",
            reason=None,
            finding_ids=[gf.id for gf in gate_findings]
        )
        self._save_state(state)

        # Wire gate-to-review promotion into the orchestrator state (BUG-003)
        from gdg_yorku_submission.preflight.secrets import promote_gate_findings
        promoted = promote_gate_findings(gate_findings)
        if promoted:
            self.write_findings("security", promoted)

    def write_findings(self, perspective: Perspective, findings: List[ReviewFinding]) -> None:
        """Appends provisional findings for a given perspective to the run state."""
        state = self._get_state()
        if state["finalized"]:
            raise RuntimeError("Cannot write findings after ID finalization.")
            
        allowed_perspectives = {"correctness", "security", "blast_radius"}
        if perspective not in allowed_perspectives:
            raise ValueError(
                f"Perspective '{perspective}' is not a valid review perspective."
            )
            
        for f in findings:
            if f.perspective != perspective:
                raise ValueError(
                    f"Finding perspective '{f.perspective}' does not match "
                    f"specialist perspective '{perspective}'"
                )
        # Deep copy to prevent external modification of state findings list/objects
        state["findings"].extend(copy.deepcopy(findings))
        self._save_state(state)

    def read_state(self) -> Dict[str, Any]:
        """Returns an isolated deep copy of the current run state, keeping redaction_context by reference."""
        state = self._get_state()
        redaction_ctx = state.get("redaction_context")
        state_copy = {k: v for k, v in state.items() if k != "redaction_context"}
        copied = copy.deepcopy(state_copy)
        copied["redaction_context"] = redaction_ctx
        return copied

    def run_specialist(
        self,
        perspective: Perspective,
        specialist_func: Callable[[], List[ReviewFinding]]
    ) -> None:
        """
        Runs a specialist reviewer function.
        Records status as 'complete' on success, or 'failed' on exception.
        Does not abort the orchestrator run on specialist failure.
        """
        allowed_perspectives = {"correctness", "security", "blast_radius"}
        if perspective not in allowed_perspectives:
            raise ValueError(
                f"Perspective '{perspective}' is not a valid review perspective "
                f"(must be one of {allowed_perspectives})."
            )

        state = self._get_state()
        if state["finalized"]:
            raise RuntimeError("Cannot run specialist after ID finalization.")
        
        try:
            findings = specialist_func()
            self.write_findings(perspective, findings)
            
            # Read state again since write_findings modified it
            state = self._get_state()
            all_ids = [f.id for f in state["findings"] if f.perspective == perspective]
            status = PerspectiveStatus(
                perspective=perspective,
                status="complete",
                reason="",
                finding_ids=all_ids
            )
            state["perspective_statuses"][perspective] = status
            self._save_state(state)
        except Exception as e:
            state = self._get_state()
            status = PerspectiveStatus(
                perspective=perspective,
                status="failed",
                reason=str(e),
                finding_ids=[]
            )
            state["perspective_statuses"][perspective] = status
            self._save_state(state)

    def finalize_ids(self) -> None:
        """Finalizes provisional findings using deterministic IDs and ordinals."""
        state = self._get_state()
        if state["finalized"]:
            return
        
        findings = state["findings"]
        finalized, id_mapping = finalize_finding_ids(findings)
        state["findings"] = finalized
        state["finalized"] = True
        
        prov_to_final = {}
        for final_id, prov_ids in id_mapping.items():
            for prov_id in prov_ids:
                prov_to_final[prov_id] = final_id
                
        for perspective, status in list(state["perspective_statuses"].items()):
            new_ids = []
            for p_id in status.finding_ids:
                if p_id in prov_to_final:
                    new_ids.append(prov_to_final[p_id])
            deduped_new_ids = []
            for n_id in new_ids:
                if n_id not in deduped_new_ids:
                    deduped_new_ids.append(n_id)
            
            state["perspective_statuses"][perspective] = PerspectiveStatus(
                perspective=status.perspective,
                status=status.status,
                reason=status.reason,
                finding_ids=deduped_new_ids
            )
        self._save_state(state)

    def compile_report(self) -> ReviewReport:
        """Compiles the finalized findings and state into a canonical ReviewReport."""
        state = self._get_state()
        if not state["finalized"]:
            self.finalize_ids()
            state = self._get_state()
            
        findings = state["findings"]
        report_findings = []
        for f in findings:
            rf = ReportFinding(
                id=f.id,
                source_agent=f.source_agent,
                perspective=f.perspective,
                severity=f.severity,
                location=f.location,
                claim=f.claim,
                evidence_ref=f.evidence_ref,
                status=f.status,
                metadata=f.metadata,
                recommended_next_action=None,
                merged_from=[]  # empty unless coordinator-level merge occurred
            )
            report_findings.append(rf)
            
        # Split active vs contested findings
        active_findings = [rf for rf in report_findings if rf.status != "contested"]
        contested_findings = [rf for rf in report_findings if rf.status == "contested"]

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for rf in active_findings:
            severity_counts[rf.severity.value] = severity_counts.get(rf.severity.value, 0) + 1
            
        # Build high_critical_findings ONLY from active findings (high_critical is subset of findings)
        high_critical = [rf for rf in active_findings if is_at_or_above_floor(rf.severity)]
        
        # Account for all findings in the ledger.
        # Contested findings are tracked in the dedicated contested list.
        ledger = AccountingLedger(
            included=[rf.id for rf in active_findings],
            merged=[],  # Specialist-level merges are handled at finalization, not coordinator-level.
            omitted=[],
            contested=[rf.id for rf in contested_findings]
        )
        
        statuses = list(state["perspective_statuses"].values())
        
        return ReviewReport(
            run_metadata={
                "run_id": self.run_id,
                "orchestrator_type": self.__class__.__name__
            },
            corpus_summary=state["corpus_summary"],
            perspective_statuses=statuses,
            gate_status=state["gate_status"],
            severity_counts=severity_counts,
            high_critical_findings=high_critical,
            findings=active_findings,
            contested_items=contested_findings,
            secret_scan_summary=state["secret_scan_summary"],
            accounting_ledger=ledger,
            validator_warnings=[]
        )


class InProcessOrchestrator(Orchestrator):
    def __init__(self) -> None:
        super().__init__()
        self._state = {}

    def _get_state(self) -> Dict[str, Any]:
        if not self.run_id:
            raise RuntimeError("Run has not been started.")
        return self._state

    def _save_state(self, state: Dict[str, Any]) -> None:
        self._state = state


_ADK_SHARED_STORE = {}

class AdkOrchestrator(Orchestrator):
    def __init__(self) -> None:
        super().__init__()

    def _get_state(self) -> Dict[str, Any]:
        if not self.run_id or self.run_id not in _ADK_SHARED_STORE:
            raise RuntimeError("Run has not been started.")
        return _ADK_SHARED_STORE[self.run_id]

    def _save_state(self, state: Dict[str, Any]) -> None:
        if not self.run_id:
            raise RuntimeError("Run has not been started.")
        # Bounded store growth to mitigate memory leak
        if len(_ADK_SHARED_STORE) >= 100 and self.run_id not in _ADK_SHARED_STORE:
            # Evict first 50 runs
            old_keys = list(_ADK_SHARED_STORE.keys())[:50]
            for k in old_keys:
                _ADK_SHARED_STORE.pop(k, None)
        _ADK_SHARED_STORE[self.run_id] = state

    @classmethod
    def clear_shared_store(cls) -> None:
        """Utility to clear store during test teardowns."""
        global _ADK_SHARED_STORE
        _ADK_SHARED_STORE.clear()
