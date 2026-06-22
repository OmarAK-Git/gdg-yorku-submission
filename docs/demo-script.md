# Out-of-Band Validator Rejection Demo Script

This document details the usage of the validator-rejection CLI tool. This CLI tool is designed to manually corrupt a compiled report in-memory and execute the report validator invariants checker, showing the rejection message.

> [!NOTE]
> This tool runs **completely out-of-band** and is **not** imported by any production FastAPI module or exposed via HTTP endpoints, satisfying safety and isolation requirements.

---

## Production Context vs. Demo Framing

> [!IMPORTANT]
> **Production "Never-Fails" Fallback Contract:** In the production runtime, the validator does **not** abort or crash the review execution. If validation checks fail, the coordinator compilation catches the errors, generates validator warnings, and seamlessly falls back to a **deterministic terminal fallback report** (refer to `compile_terminal_report` in `orchestrator.py`).
>
> **Demo Hook Isolation:** The CLI hook (`demo_hooks.py`) isolates and demonstrates the raw detection layer of the validator. It purposefully runs the validator directly and aborts with a non-zero exit code (`1`) to explicitly highlight the invariant checks on camera.

---

## Action 1: Dropping High findings (`drop-high`)

> [!NOTE]
> **Last-Line-of-Defense Backstop:** In production, the coordinator agent compiles findings via a schema-locked component that does not omit high/critical severity findings. Therefore, this scenario validates the validator's **backstop** for an upstream-prevented state, rather than representing a standard end-to-end failure path.

This action ingests the repository zip archive, generates input findings using baseline security scanners, and removes one of the HIGH-severity findings from the report, mapping it into the omitted ledger. This violates the conservation accounting invariant that forbids omitting high/critical findings.

### Execution Command
```bash
python -m gdg_yorku_submission.demo_hooks drop-high samples/driftstore.zip
```

### Expected Output
```text
Ingesting zip file: samples/driftstore.zip
Generated 7 input findings.
Valid terminal report compiled. Action to apply: 'drop-high'
Deliberately dropping HIGH finding: 3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c
Running report validation invariants check...

=== VALIDATOR REJECTED REPORT ===
Validator Invariant Violation: Forbidden omission of high/critical finding '3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c' (severity: high)
=================================
```

---

## Action 2: Out of Bounds Location Coordinates (`corrupt-location`)

This action takes a valid terminal report and manually corrupts the location line coordinates of the first finding (setting lines to `9999-10000` which are out of bounds for the source file).

### Execution Command
```bash
python -m gdg_yorku_submission.demo_hooks corrupt-location samples/driftstore.zip
```

### Expected Output
```text
Ingesting zip file: samples/driftstore.zip
Generated 7 input findings.
Valid terminal report compiled. Action to apply: 'corrupt-location'
Deliberately corrupting coordinates of finding: 3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c
Running report validation invariants check...

=== VALIDATOR REJECTED REPORT ===
Validator Invariant Violation: Finding '3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c' location lines 9999-10000 are out of bounds for 'src/app.py' (original line count: 37)
=================================
```

---

## Action 3: Out of Bounds Evidence Reference (`corrupt-evidence-ref`)

This action takes a valid terminal report and manually corrupts the `evidence_ref` coordinates of the first finding to point to out-of-bounds coordinates `9999-10000` for the source file, violating the evidence-coordinate existence check.

### Execution Command
```bash
python -m gdg_yorku_submission.demo_hooks corrupt-evidence-ref samples/driftstore.zip
```

### Expected Output
```text
Ingesting zip file: samples/driftstore.zip
Generated 7 input findings.
Valid terminal report compiled. Action to apply: 'corrupt-evidence-ref'
Deliberately corrupting coordinates of finding: 3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c
Running report validation invariants check...

=== VALIDATOR REJECTED REPORT ===
Validator Invariant Violation: Finding '3148dac7429cfe13fa30ceea4373f31cf8c871b5b19cb0016fdd833fd43dd53c' evidence_ref lines 9999-10000 are out of bounds for 'src/app.py' (original line count: 37) in ref 'file:src/app.py#9999-10000'
=================================
```

---

## Action 4: Redaction and Invariant Verification (`leak-secret`)

This action validates the system-wide **secret redaction invariant**. Rather than performing a demo-local post-scrub or manual injection, it proves that the real pipeline never emits raw secrets onto the report/frontend surface because the corpus text is fully redacted at ingestion/build time (pre-flight). 

The compiled report JSON includes a `secret_scan_summary` that carries only salted hashes (fingerprints) of detected credentials for tracking, but never the raw secret values.

### Execution Command
```bash
python -m gdg_yorku_submission.demo_hooks leak-secret samples/driftstore.zip
```

### Expected Output
```text
Ingesting zip file: samples/driftstore.zip
Generated 7 input findings.
Valid terminal report compiled. Action to apply: 'leak-secret'

=== PASS: REDACTION INVARIANT VALIDATED ===
Raw secret was found in the source file original text.
Raw secret was NOT found in the source file redacted text.
Raw secret was NOT found in the final compiled report JSON.
Salted fingerprint 'sha256_fc93da30f64d93c6_2345' is present in the report JSON.
============================================
```
