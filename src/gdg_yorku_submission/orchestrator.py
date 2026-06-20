import uuid
import abc
import copy
import logging
from typing import List, Dict, Any, Callable, Union, Tuple, Optional

logger = logging.getLogger(__name__)
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
        from gdg_yorku_submission.budget import RunBudget
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
            "budget": RunBudget().model_dump(),
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

    def set_run_metadata(self, key: str, value: Any) -> None:
        """Sets a key-value pair in the run metadata."""
        state = self._get_state()
        if "run_metadata" not in state:
            state["run_metadata"] = {}
        state["run_metadata"][key] = value
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
        specialist_func: Callable[[], Union[List[ReviewFinding], Tuple[List[ReviewFinding], str, str]]]
    ) -> None:
        """
        Runs a specialist reviewer function.
        Records status as 'complete' on success (or custom status if returned as tuple),
        or 'failed' on exception.
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
            result = specialist_func()
            if isinstance(result, tuple):
                if len(result) != 3:
                    raise ValueError(
                        f"Specialist returned tuple of length {len(result)} "
                        f"but expected exactly 3: (findings, status, reason)"
                    )
                findings, custom_status, custom_reason = result
            else:
                findings = result
                custom_status = "complete"
                custom_reason = ""

            self.write_findings(perspective, findings)
            
            # Read state again since write_findings modified it
            state = self._get_state()
            all_ids = [f.id for f in state["findings"] if f.perspective == perspective]
            status = PerspectiveStatus(
                perspective=perspective,
                status=custom_status,
                reason=custom_reason,
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

    def compile_terminal_report(self) -> ReviewReport:
        """
        Compiles the terminal report (fallback).
        Every input finding is Included verbatim, ordered by severity then path.
        No merges, empty omissions, empty contested (unless input is contested).
        Zero LLM budget required.
        """
        state = self._get_state()
        if not state["finalized"]:
            self.finalize_ids()
            state = self._get_state()
            
        findings = state["findings"]
        corpus = self.get_corpus()
        
        from gdg_yorku_submission.coordinator import parse_evidence_ref, validate_report_invariants
        
        report_findings = []
        terminal_warnings = ["Coordinator compilation failed or was bypassed. Active terminal fallback report."]
        
        for f in findings:
            valid_refs = []
            stripped_refs = []
            for ref in f.evidence_ref:
                is_valid = True
                try:
                    ref_path, ref_start, ref_end = parse_evidence_ref(ref)
                    corpus_key = None
                    for k in corpus.keys():
                        if k.lower() == ref_path.replace("\\", "/").lower():
                            corpus_key = k
                            break
                    if corpus_key is None:
                        is_valid = False
                    else:
                        corpus_file = corpus[corpus_key]
                        if ref_start < 1 or ref_end > corpus_file.original_line_count or ref_start > ref_end:
                            is_valid = False
                except Exception:
                    is_valid = False
                
                if is_valid:
                    valid_refs.append(ref)
                else:
                    stripped_refs.append(ref)
            
            if stripped_refs:
                terminal_warnings.append(
                    f"Finding {f.id} evidence_ref stripped: {', '.join(stripped_refs)}"
                )
                
            rf = ReportFinding(
                id=f.id,
                source_agent=f.source_agent,
                perspective=f.perspective,
                severity=f.severity,
                location=f.location,
                claim=f.claim,
                evidence_ref=valid_refs,
                status=f.status,
                metadata=f.metadata,
                recommended_next_action=f"Verify finding in {f.location.path} lines {f.location.line_start}-{f.location.line_end}.",
                merged_from=[]
            )
            report_findings.append(rf)
            
        # Sanitize secret_scan_summary gate findings evidence_refs (R1a)
        sanitized_gate_findings = []
        for gf in state.get("secret_scan_summary", []):
            valid_refs = []
            stripped_refs = []
            for ref in gf.evidence_ref:
                is_valid = True
                try:
                    ref_path, ref_start, ref_end = parse_evidence_ref(ref)
                    corpus_key = None
                    for k in corpus.keys():
                        if k.lower() == ref_path.replace("\\", "/").lower():
                            corpus_key = k
                            break
                    if corpus_key is None:
                        is_valid = False
                    else:
                        corpus_file = corpus[corpus_key]
                        if ref_start < 1 or ref_end > corpus_file.original_line_count or ref_start > ref_end:
                            is_valid = False
                except Exception:
                    is_valid = False
                
                if is_valid:
                    valid_refs.append(ref)
                else:
                    stripped_refs.append(ref)
            
            if stripped_refs:
                terminal_warnings.append(
                    f"Gate Finding {gf.id} evidence_ref stripped: {', '.join(stripped_refs)}"
                )
            
            gf_copy = gf.model_copy(update={"evidence_ref": valid_refs})
            sanitized_gate_findings.append(gf_copy)

        # Order report findings by severity (descending rank) then path
        report_findings.sort(key=lambda x: (-x.severity.rank, x.location.path, x.location.line_start))
        
        # Split active vs contested findings
        active_findings = [rf for rf in report_findings if rf.status != "contested"]
        contested_findings = [rf for rf in report_findings if rf.status == "contested"]
    
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for rf in active_findings:
            severity_counts[rf.severity.value] = severity_counts.get(rf.severity.value, 0) + 1
            
        high_critical = [rf for rf in active_findings if is_at_or_above_floor(rf.severity)]
        
        ledger = AccountingLedger(
            included=[rf.id for rf in active_findings],
            merged=[],
            omitted=[],
            contested=[rf.id for rf in contested_findings]
        )
        
        statuses = list(state["perspective_statuses"].values())
        
        report = ReviewReport(
            run_metadata={
                **state.get("run_metadata", {}),
                "run_id": self.run_id,
                "orchestrator_type": self.__class__.__name__,
                "compilation_mode": "terminal_fallback"
            },
            corpus_summary=state["corpus_summary"],
            perspective_statuses=statuses,
            gate_status=state["gate_status"],
            severity_counts=severity_counts,
            high_critical_findings=high_critical,
            findings=active_findings,
            contested_items=contested_findings,
            secret_scan_summary=sanitized_gate_findings,
            accounting_ledger=ledger,
            validator_warnings=terminal_warnings
        )
        
        errors = validate_report_invariants(report, findings, corpus)
        if errors:
            logger.warning(f"Terminal fallback report validation warnings: {errors}")
            report.validator_warnings.extend(errors)
            
        return report

    def compile_report(self, gemini_client: Optional[Any] = None) -> ReviewReport:
        """
        Compiles the finalized findings and state into a canonical ReviewReport.
        Attempts coordinator compilation first, falling back to a deterministic terminal report.
        """
        state = self._get_state()
        if not state["finalized"]:
            self.finalize_ids()
            state = self._get_state()
            
        findings = state["findings"]
        statuses = list(state["perspective_statuses"].values())
        gate_status = state["gate_status"]
        
        from gdg_yorku_submission.coordinator import run_coordinator_compilation, validate_report_invariants
        
        corpus = self.get_corpus()
        
        try:
            # Run coordinator compilation
            compiled_findings, contested_items, ledger = run_coordinator_compilation(
                self,
                findings,
                statuses,
                gate_status,
                gemini_client=gemini_client
            )
            
            # Build the report
            # Split active vs contested findings
            active_findings = [rf for rf in compiled_findings if rf.status != "contested"]
            
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            for rf in active_findings:
                severity_counts[rf.severity.value] = severity_counts.get(rf.severity.value, 0) + 1
                
            high_critical = [rf for rf in active_findings if is_at_or_above_floor(rf.severity)]
            
            report = ReviewReport(
                run_metadata={
                    **state.get("run_metadata", {}),
                    "run_id": self.run_id,
                    "orchestrator_type": self.__class__.__name__,
                    "compilation_mode": "coordinated"
                },
                corpus_summary=state["corpus_summary"],
                perspective_statuses=statuses,
                gate_status=state["gate_status"],
                severity_counts=severity_counts,
                high_critical_findings=high_critical,
                findings=active_findings,
                contested_items=contested_items,
                secret_scan_summary=state["secret_scan_summary"],
                accounting_ledger=ledger,
                validator_warnings=[]
            )
            
            # Validate invariants
            errors = validate_report_invariants(report, findings, corpus)
            if errors:
                raise ValueError(f"Report validation failed: {errors}")
                
            return report
            
        except Exception as e:
            logger.warning(f"Coordinator compilation failed or rejected, falling back to terminal report. Error: {e}")
            return self.compile_terminal_report()



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
