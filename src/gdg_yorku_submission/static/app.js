// Mock Report Data for manual demo showcase and testing without live server uploads
const MOCK_DEMO_REPORT = {
  "run_metadata": {
    "orchestrator_type": "AdkOrchestrator",
    "start_time": "2026-06-21T17:30:15.123-04:00",
    "duration_ms": 2345,
    "compilation_mode": "coordinated",
    "budget_remaining": "85.2% token allocation",
    "debate_transcript": {
      "engaged": true,
      "seed_findings": 2,
      "stop_reason": "consensus_reached",
      "final_score": { "challenger": 2.0, "defender": 1.0 },
      "scoreboard": [
        { "round": 1, "challenger": 0.0, "defender": 0.0 },
        { "round": 2, "challenger": 2.0, "defender": 1.0 }
      ],
      "rounds": [
        {
          "round": 1,
          "messages": [
            { "role": "challenger", "message": "Proposed: Missing auth decorator on write route '/admin/delete-product' — attacker-reachable destructive endpoint. (Severity: high)" },
            { "role": "challenger", "message": "Proposed: Unsafe pickle.loads on request query data enables arbitrary code execution. (Severity: low)" },
            { "role": "defender", "message": "Proposed: The '/admin/delete-product' route may be guarded by upstream gateway middleware not visible in this corpus — request grounded evidence before scoring high. (Severity: info)" },
            { "role": "defender", "message": "Proposed: 'requests' is pinned to 2.25.1; flag as outdated dependency (CVE-2022-28108). (Severity: info)" }
          ]
        },
        {
          "round": 2,
          "messages": [
            { "role": "defender", "message": "Scored C-R1-P1: modify — concede the route lacks an in-repo auth dependency; downgrade my middleware assumption. Auth finding stands." },
            { "role": "defender", "message": "Scored C-R1-P2: accept — pickle.loads on untrusted input is indefensible; finding survives." },
            { "role": "challenger", "message": "Scored D-R1-P1: reject — no Depends(...) or decorator exists at src/app.py#54-57; the gateway claim is ungrounded in the corpus." },
            { "role": "challenger", "message": "Scored D-R1-P2: reject — the requests pin is a maintenance concern, not on an exploitable path in this codebase; out-of-scope for the security floor." }
          ]
        }
      ],
      "resolutions": [
        { "claim": "Missing auth decorator on write route '/admin/delete-product'", "severity": "high", "resolution": "survived", "closed_reason": null },
        { "claim": "Unsafe deserialize call to pickle.loads on request query data", "severity": "low", "resolution": "survived", "closed_reason": null },
        { "claim": "Contested outdated packages: requests dependency is pinned to 2.25.1", "severity": "info", "resolution": "contested", "closed_reason": "Challenger rejected as not on an exploitable path; defender held it as a maintenance concern — retained as contested rather than dropped." }
      ]
    }
  },
  "corpus_summary": {
    "file_count": 8,
    "total_bytes": 14280,
    "skipped_files": 1,
    "skipped_log": {
      "samples/driftstore/tests/test_dummy.py.tmp": {
        "skipped_reason": "system_exclude: Large temporary file skipped"
      }
    }
  },
  "perspective_statuses": [
    {
      "perspective": "correctness",
      "status": "complete",
      "reason": "Divergence check executed successfully",
      "finding_ids": ["f-id-correct-1", "f-id-correct-2"]
    },
    {
      "perspective": "security",
      "status": "complete",
      "reason": "AST baseline seeded a 2-round adversarial debate (Claude challenger vs Gemini defender). Consensus reached.",
      "finding_ids": ["f-id-sec-ast-1", "f-id-sec-ast-2", "f-id-sec-sec-1"]
    },
    {
      "perspective": "blast_radius",
      "status": "disabled",
      "reason": "Orbit / GitLab Knowledge Graph adapter unconfigured",
      "finding_ids": []
    }
  ],
  "gate_status": {
    "status": "complete",
    "reason": "Pre-flight credential scan completed successfully",
    "finding_ids": ["f-id-sec-sec-1"]
  },
  "severity_counts": {
    "critical": 0,
    "high": 2,
    "medium": 2,
    "low": 1,
    "info": 0
  },
  "high_critical_findings": [
    {
      "id": "cb1a79f04bbdbce83a45c38668798e4a9e5b62a6321287c805a691bc2e84c98f",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 8,
        "line_end": 8
      },
      "claim": "Google API Key exposed in tracked source code",
      "evidence_ref": ["file:src/app.py#8"],
      "status": "active",
      "recommended_next_action": "Revoke the API key immediately in the Google Cloud Platform console. Move credentials to an environment file (.env) that is gitignored.",
      "merged_from": []
    },
    {
      "id": "e3020610360a0b2304910cf90df93108c908581e285a9bc8926a9f4c398e82ef",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 54,
        "line_end": 57
      },
      "claim": "AST Baseline: Missing auth decorator on write route '/admin/delete-product'",
      "evidence_ref": ["file:src/app.py#54-57"],
      "status": "active",
      "recommended_next_action": "Add an authentication dependency or decorator like Depends(get_current_active_user) to restrict this write API.",
      "merged_from": ["prov-auth-1", "prov-auth-2"]
    }
  ],
  "findings": [
    {
      "id": "cb1a79f04bbdbce83a45c38668798e4a9e5b62a6321287c805a691bc2e84c98f",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 8,
        "line_end": 8
      },
      "claim": "Google API Key exposed in tracked source code",
      "evidence_ref": ["file:src/app.py#8"],
      "status": "active",
      "recommended_next_action": "Revoke the API key immediately in the Google Cloud Platform console. Move credentials to an environment file (.env) that is gitignored.",
      "merged_from": []
    },
    {
      "id": "e3020610360a0b2304910cf90df93108c908581e285a9bc8926a9f4c398e82ef",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 54,
        "line_end": 57
      },
      "claim": "AST Baseline: Missing auth decorator on write route '/admin/delete-product'",
      "evidence_ref": ["file:src/app.py#54-57"],
      "status": "active",
      "recommended_next_action": "Add an authentication dependency or decorator like Depends(get_current_active_user) to restrict this write API.",
      "merged_from": ["prov-auth-1", "prov-auth-2"]
    },
    {
      "id": "d04a6015b6cd98eb931e2478e87d0e49be8b7b2a6321287c805a691bc2e84c98e",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "medium",
      "location": {
        "path": "src/app.py",
        "line_start": 22,
        "line_end": 26
      },
      "claim": "Correctness Divergence: Retry mechanism has a backoff_factor of 2.0, but SPEC.md Section 4 states backoff_factor must be 1.5",
      "evidence_ref": ["file:SPEC.md#14-15", "file:src/app.py#22"],
      "status": "active",
      "recommended_next_action": "Modify the backoff_factor initialization parameter in src/app.py from 2.0 to 1.5 to align with specification requirements.",
      "merged_from": []
    },
    {
      "id": "782f91a0cde0e35905187e1a3bc79e8a9d03281e285a9bc8926a9f4c398e8111",
      "source_agent": "correctness_agent",
      "perspective": "correctness",
      "severity": "medium",
      "location": {
        "path": "src/app.py",
        "line_start": 35,
        "line_end": 35
      },
      "claim": "Correctness Divergence: Default max connection pool size is set to 20, but SPEC.md Section 2 specifies 10",
      "evidence_ref": ["file:SPEC.md#8", "file:src/app.py#35"],
      "status": "active",
      "recommended_next_action": "Change max_connections default value in the DatabasePool class definition to 10.",
      "merged_from": []
    },
    {
      "id": "993a4b08b3c9ef9104810cf90df93108c908581e285a9bc8926a9f4c398e8122",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "low",
      "location": {
        "path": "src/app.py",
        "line_start": 91,
        "line_end": 91
      },
      "claim": "AST Baseline: Unsafe deserialize call to pickle.loads on request query data",
      "evidence_ref": ["file:src/app.py#91"],
      "status": "active",
      "recommended_next_action": "Migrate deserialization logic to json.loads or utilize safe configuration mappings rather than arbitrary Python pickle evaluation.",
      "merged_from": []
    }
  ],
  "contested_items": [
    {
      "id": "8f39a061bce839e204910cf90df93108c908581e285a9bc8926a9f4c398e8def",
      "source_agent": "security_debate",
      "perspective": "security",
      "severity": "info",
      "location": {
        "path": "pyproject.toml",
        "line_start": 12,
        "line_end": 12
      },
      "claim": "Adversarial Debate: Contested outdated packages: requests dependency is pinned to 2.25.1",
      "evidence_ref": ["file:pyproject.toml#12"],
      "status": "contested",
      "recommended_next_action": "Upgrade requests to >=2.28.0 to resolve CVE-2022-28108. (Challenger contested finding, defended as out-of-scope for correctness baseline).",
      "merged_from": []
    }
  ],
  "secret_scan_summary": [
    {
      "id": "f-id-sec-sec-1",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "high",
      "location": {
        "path": "src/app.py",
        "line_start": 8,
        "line_end": 8
      },
      "claim": "Google API Key exposed in tracked source code",
      "evidence_ref": [],
      "secret_type": "Google API Key",
      "fingerprint": "salted_sha256_5a9b...7c805a91",
      "exposure_status": "prompt_exposed"
    },
    {
      "id": "f-id-sec-sec-2",
      "source_agent": "preflight_secret_gate",
      "perspective": "security",
      "severity": "info",
      "location": {
        "path": ".env",
        "line_start": 2,
        "line_end": 2
      },
      "claim": "Database password configuration string in gitignored file",
      "evidence_ref": [],
      "secret_type": "Database Password",
      "fingerprint": "salted_sha256_e10c...3d25ef90",
      "exposure_status": "ignored_by_root_gitignore"
    }
  ],
  "accounting_ledger": {
    "included": [
      "cb1a79f04bbdbce83a45c38668798e4a9e5b62a6321287c805a691bc2e84c98f",
      "e3020610360a0b2304910cf90df93108c908581e285a9bc8926a9f4c398e82ef",
      "d04a6015b6cd98eb931e2478e87d0e49be8b7b2a6321287c805a691bc2e84c98e",
      "782f91a0cde0e35905187e1a3bc79e8a9d03281e285a9bc8926a9f4c398e8111",
      "993a4b08b3c9ef9104810cf90df93108c908581e285a9bc8926a9f4c398e8122"
    ],
    "merged": [
      {
        "output_id": "e3020610360a0b2304910cf90df93108c908581e285a9bc8926a9f4c398e82ef",
        "input_ids": ["prov-auth-1", "prov-auth-2"]
      }
    ],
    "omitted": [
      {
        "id": "prov-style-issue-1",
        "reason": "Styling consistency finding below reporting floor (high) omitted."
      }
    ],
    "contested": [
      "8f39a061bce839e204910cf90df93108c908581e285a9bc8926a9f4c398e8def"
    ]
  },
  "validator_warnings": []
};

// State to store current report
let currentReport = null;
let activeTab = 'all';
let activePerspectives = new Set(['all']); // Perspective filter state

document.addEventListener('DOMContentLoaded', () => {
  initDragAndDrop();
  initTabs();
  initPerspectiveFilters();

  // Set up mock button handler
  const demoBtn = document.getElementById('demo-load-btn');
  demoBtn.addEventListener('click', () => {
    loadReportData(MOCK_DEMO_REPORT);
  });

  // Home button handler
  const homeBtn = document.getElementById('home-btn');
  homeBtn.addEventListener('click', () => {
    resetToUploadView();
  });

  // Download report handler
  const downloadBtn = document.getElementById('download-report-btn');
  downloadBtn.addEventListener('click', () => {
    downloadReport();
  });

  // Adversarial debate viewer handlers
  document.getElementById('view-debate-btn').addEventListener('click', openDebateModal);
  document.getElementById('debate-modal-close').addEventListener('click', closeDebateModal);
  document.getElementById('debate-modal').addEventListener('click', (e) => {
    // Click on the dimmed backdrop (not the dialog body) closes the modal.
    if (e.target.id === 'debate-modal') closeDebateModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDebateModal();
  });
});

/**
 * Pull the adversarial debate transcript out of a report, if one was recorded.
 * Real runs attach it at run_metadata.debate_transcript; returns null when the
 * debate never engaged (disabled, budget-skipped, or AST-only fallback).
 */
function getDebateTranscript(report) {
  const t = report && report.run_metadata && report.run_metadata.debate_transcript;
  if (!t || t.engaged === false) return null;
  if (!Array.isArray(t.rounds) || t.rounds.length === 0) return null;
  return t;
}

/**
 * Initialize Drag and Drop Upload System
 */
function initDragAndDrop() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  // Highlighting drag states
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleRepositoryUpload(files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleRepositoryUpload(fileInput.files[0]);
    }
  });
}

/**
 * Send zip archive to FastAPI backend for live, streamed analysis.
 * Consumes the Server-Sent Event stream from POST /review/stream so each pipeline
 * stage is shown as it happens, then renders the dashboard from the terminal report.
 * Falls back to the blocking POST /review if streaming is unavailable.
 * @param {File} file
 */
async function handleRepositoryUpload(file) {
  if (file.type !== 'application/zip' && !file.name.endsWith('.zip')) {
    alert('Invalid file format. Please upload a repository packaged as a .zip file.');
    return;
  }

  const dropzone = document.getElementById('dropzone');
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');

  // Transition UI to progress view and build the live step tracker.
  dropzone.classList.add('hidden');
  progressContainer.classList.remove('hidden');
  progressFill.style.width = '4%';
  statusText.textContent = 'Uploading repository archive...';
  buildStepTracker();

  try {
    const result = await streamReview(file);
    if (result.report) {
      finishWithReport(result.report);
    } else {
      // A pipeline-level error event was already surfaced to the user.
      resetUploadUI();
    }
  } catch (streamErr) {
    // Transport-level failure (endpoint missing, no streaming support, network).
    // Fall back to the blocking endpoint so the dashboard still renders.
    console.warn('Streaming unavailable, falling back to blocking /review:', streamErr);
    hideStepTracker();
    progressFill.style.width = '45%';
    statusText.textContent = 'Streaming unavailable - running analysis...';
    try {
      const report = await blockingReview(file);
      finishWithReport(report);
    } catch (error) {
      console.error('Analysis failed:', error);
      alert(`Orchestrator Error: ${error.message}`);
      resetUploadUI();
    }
  }
}

/**
 * Canonical ordered pipeline stages, mirroring the backend SSE step names.
 */
const PIPELINE_STEPS = [
  { key: 'ingestion', label: 'Extracting & hardening archive' },
  { key: 'secret_gate', label: 'Pre-flight secret scan' },
  { key: 'correctness', label: 'Correctness specialist' },
  { key: 'security', label: 'Security specialist (AST + debate)' },
  { key: 'blast_radius', label: 'Blast-radius specialist' },
  { key: 'compile', label: 'Compiling final report' },
];

/**
 * Stream POST /review/stream and drive the live step tracker.
 * @param {File} file
 * @returns {Promise<{report: Object|null}>} report on success, {report:null} if a
 *   pipeline error event was handled. Throws only on transport failure (triggers fallback).
 */
async function streamReview(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/review/stream', { method: 'POST', body: formData });
  const ctype = response.headers.get('content-type') || '';
  if (!response.ok || !response.body || !ctype.includes('text/event-stream')) {
    throw new Error('stream-unsupported');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalReport = null;
  let pipelineError = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex;
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawFrame = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const evt = parseSseFrame(rawFrame);
      if (!evt) continue;

      if (evt.event === 'step') {
        updateStepTracker(evt.data);
      } else if (evt.event === 'debate') {
        handleDebateEvent(evt.data);
      } else if (evt.event === 'report') {
        finalReport = evt.data;
      } else if (evt.event === 'error') {
        pipelineError = evt.data;
      }
    }
  }

  if (pipelineError) {
    markStepError(pipelineError);
    alert(`Orchestrator Error: ${pipelineError.message || 'Review pipeline failed.'}`);
    return { report: null };
  }
  if (!finalReport) {
    // Stream ended without a report and without an error frame  treat as a transport
    // failure so we fall back to the blocking endpoint.
    throw new Error('stream-ended-without-report');
  }
  return { report: finalReport };
}

/**
 * Blocking fallback: POST /review and return the parsed report.
 * @param {File} file
 */
async function blockingReview(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/review', { method: 'POST', body: formData });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Review run aborted or failed.');
  }
  return await response.json();
}

/**
 * Parse a single raw SSE frame into {event, data}. Returns null if it has no data line.
 * @param {string} rawFrame
 */
function parseSseFrame(rawFrame) {
  let eventName = 'message';
  const dataLines = [];
  rawFrame.split('\n').forEach(line => {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  });
  if (dataLines.length === 0) return null;
  try {
    return { event: eventName, data: JSON.parse(dataLines.join('\n')) };
  } catch (e) {
    return null;
  }
}

/**
 * Build the live step tracker rows inside the progress container.
 */
function buildStepTracker() {
  const container = document.getElementById('upload-progress-container');
  let tracker = document.getElementById('live-steps');
  if (tracker) tracker.remove();

  tracker = document.createElement('ul');
  tracker.id = 'live-steps';
  tracker.className = 'live-steps';

  PIPELINE_STEPS.forEach(step => {
    const li = document.createElement('li');
    li.className = 'live-step is-pending';
    li.id = `live-step-${step.key}`;

    // Icon glyph (pending ring / spinner / check / x) is rendered by CSS from the
    // row's state class, so the element is intentionally empty.
    const icon = document.createElement('span');
    icon.className = 'live-step-icon';

    const label = document.createElement('span');
    label.className = 'live-step-label';
    label.textContent = step.label;

    li.appendChild(icon);
    li.appendChild(label);
    tracker.appendChild(li);
  });

  container.appendChild(tracker);
  buildActivityConsole();
}

/**
 * Update a single step row + the progress bar from a `step` SSE event.
 * @param {Object} data {step, status, label, index, total}
 */
function updateStepTracker(data) {
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');
  const total = data.total || PIPELINE_STEPS.length;
  const index = data.index || 0;

  if (data.label) statusText.textContent = data.label;

  // Running: bar sits just before the step completes; Complete: bar reaches index/total.
  const fraction = data.status === 'complete'
    ? index / total
    : Math.max(0, (index - 1)) / total + (0.5 / total);
  progressFill.style.width = `${Math.min(100, Math.round(fraction * 100))}%`;

  const row = document.getElementById(`live-step-${data.step}`);
  if (!row) return;

  row.classList.remove('is-pending', 'is-running', 'is-complete', 'is-error');
  if (data.status === 'complete') {
    row.classList.add('is-complete');
    stopStepFlavor();
    appendActivity(`${data.label || data.step} — done`, 'good');
  } else {
    row.classList.add('is-running');
    appendActivity(`▸ ${data.label || data.step}`, 'accent');
    startStepFlavor(data.step);
  }
}

/**
 * Mark the step that failed (from a terminal `error` event).
 * @param {Object} data {step, message}
 */
function markStepError(data) {
  stopStepFlavor();
  const row = document.getElementById(`live-step-${data.step}`);
  if (row) {
    row.classList.remove('is-pending', 'is-running', 'is-complete');
    row.classList.add('is-error');
  }
  appendActivity(`✕ ${data.step} failed — ${data.message || 'pipeline error'}`, 'warn');
}

function hideStepTracker() {
  stopStepFlavor();
  const tracker = document.getElementById('live-steps');
  if (tracker) tracker.remove();
  const consoleEl = document.getElementById('activity-console');
  if (consoleEl) consoleEl.remove();
}

/* --------------------------------------------------------------------------- *
 * Live activity console — a "behind the scenes" debug feed that keeps the user
 * informed (and entertained) across the 2-3 min run. Real SSE step events drive
 * the headline lines; per-step flavor pools fill the quiet stretches, with the
 * security step getting a Crucible-style adversarial-debate scoreboard.
 * --------------------------------------------------------------------------- */
let activityTimer = null;
let activityStartTime = 0;
let debateState = null;
let realDebateActive = false; // true once authentic SSE debate events arrive

const STEP_FLAVOR = {
  ingestion: [
    'unzipping archive into hardened sandbox…',
    'rejecting path-traversal & zip-slip entries…',
    'normalizing line endings and encodings…',
    'computing per-file size & type manifest…',
  ],
  secret_gate: [
    'scanning for high-entropy strings…',
    'matching Google / AWS / private-key signatures…',
    'cross-checking .gitignore exposure status…',
    'salting + hashing matches (no raw secrets leave the box)…',
  ],
  correctness: [
    'reading SPEC.md intent vs. implemented behavior…',
    'diffing documented requirements against code paths…',
    'grounding each claim to exact file + line evidence…',
    'flagging divergences for the coordinator…',
  ],
  blast_radius: [
    'querying Orbit knowledge graph over GitLab…',
    'resolving call sites for changed symbols…',
    'walking import edges to estimate impact…',
    'ranking findings by reachability…',
  ],
  compile: [
    'merging overlapping findings…',
    'enforcing conservation ledger (nothing dropped silently)…',
    'validating evidence coordinates in-bounds…',
    'finalizing stable finding IDs…',
  ],
};

const DEBATE_CHALLENGER = [
  'probing auth surface on write routes…',
  'arguing the deserialize path is attacker-reachable…',
  'pushing on the SQL string concatenation…',
  'claiming the path join is exploitable via ../…',
  'questioning whether verify=False ships to prod…',
];
const DEBATE_DEFENDER = [
  'rebuts: route is guarded by Depends(get_current_user)…',
  'counters: input is schema-validated upstream…',
  'concedes the point — finding survives…',
  'argues out-of-scope for the correctness baseline…',
  'demands grounded evidence before scoring…',
];

function buildActivityConsole() {
  const container = document.getElementById('upload-progress-container');
  let consoleEl = document.getElementById('activity-console');
  if (consoleEl) consoleEl.remove();

  consoleEl = document.createElement('div');
  consoleEl.id = 'activity-console';
  consoleEl.className = 'activity-console';

  const header = document.createElement('div');
  header.className = 'activity-console-header';
  header.textContent = 'behind the scenes';
  consoleEl.appendChild(header);

  const body = document.createElement('div');
  body.id = 'activity-console-body';
  consoleEl.appendChild(body);

  container.appendChild(consoleEl);
  activityStartTime = Date.now();
  debateState = null;
  realDebateActive = false;
  appendActivity('analysis pipeline initialized', 'accent');
}

/**
 * Render a real debate event streamed from the backend (phase ∈
 * start|round|scoreboard|complete). The first real event silences the synthetic
 * security flavor so the authentic rounds/scores take over.
 */
function handleDebateEvent(d) {
  if (!realDebateActive) {
    realDebateActive = true;
    stopStepFlavor();
  }
  if (!d || !d.phase) return;

  if (d.phase === 'start') {
    appendActivity(
      `adversarial debate engaged · ${d.seed_findings} seed finding(s) · Claude vs Gemini`,
      'accent'
    );
  } else if (d.phase === 'round') {
    const actor = d.actor === 'defender' ? 'Gemini (defender)' : 'Claude (challenger)';
    const kind = d.actor === 'defender' ? 'defender' : 'challenger';
    const bits = [];
    if (d.scored) bits.push(`scored ${d.scored}`);
    if (d.proposed) bits.push(`proposed ${d.proposed}`);
    appendActivity(`round ${d.round} · ${actor}${bits.length ? ' — ' + bits.join(', ') : ''}`, kind);
  } else if (d.phase === 'scoreboard') {
    appendActivity(`scoreboard · challenger ${d.challenger} · defender ${d.defender}`, '');
  } else if (d.phase === 'complete') {
    const reason = d.stop_reason ? ` (${d.stop_reason})` : '';
    appendActivity(`debate resolved · ${d.survived} survived · ${d.contested} contested${reason}`, 'good');
  }
}

function elapsedStamp() {
  const s = Math.floor((Date.now() - activityStartTime) / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

/**
 * Append one timestamped line. `kind` ∈ accent|good|warn|challenger|defender|''.
 */
function appendActivity(msg, kind = '') {
  const body = document.getElementById('activity-console-body');
  const consoleEl = document.getElementById('activity-console');
  if (!body || !consoleEl) return;

  const line = document.createElement('div');
  line.className = 'activity-line' + (kind ? ` is-${kind}` : '');

  const time = document.createElement('span');
  time.className = 'activity-time';
  time.textContent = elapsedStamp();

  const text = document.createElement('span');
  text.className = 'activity-msg';
  text.textContent = msg;

  line.appendChild(time);
  line.appendChild(text);
  body.appendChild(line);

  // Keep the log bounded and pinned to the newest line.
  while (body.children.length > 80) body.removeChild(body.firstChild);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Start rotating flavor lines for the running step. The security step runs the
 * Crucible-style debate scoreboard (challenger vs defender, rounds, points).
 */
function startStepFlavor(stepKey) {
  stopStepFlavor();

  if (stepKey === 'security') {
    debateState = { round: 1, turn: 'challenger', challenger: 0, defender: 0 };
    appendActivity('adversarial debate engaged · Claude (challenger) vs Gemini (defender)', 'accent');
    activityTimer = setInterval(tickDebate, 2400);
    return;
  }

  const pool = STEP_FLAVOR[stepKey];
  if (!pool) return;
  activityTimer = setInterval(() => appendActivity(pick(pool)), 2600);
}

function tickDebate() {
  if (!debateState) return;
  const st = debateState;

  if (st.turn === 'challenger') {
    appendActivity(`round ${st.round} · Claude ${pick(DEBATE_CHALLENGER)}`, 'challenger');
    st.turn = 'defender';
  } else {
    const line = pick(DEBATE_DEFENDER);
    appendActivity(`round ${st.round} · Gemini ${line}`, 'defender');
    // Score the exchange: a concession favors the challenger's finding.
    if (line.includes('survives') || line.includes('concedes')) st.challenger += 1;
    else st.defender += 1;
    appendActivity(`scoreboard · challenger ${st.challenger} · defender ${st.defender}`, '');
    st.turn = 'challenger';
    st.round += 1;
  }
}

function stopStepFlavor() {
  if (activityTimer) {
    clearInterval(activityTimer);
    activityTimer = null;
  }
}

/**
 * Transition from the progress view to the rendered dashboard.
 * @param {Object} report
 */
function finishWithReport(report) {
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  const statusText = document.getElementById('progress-status-text');

  progressFill.style.width = '100%';
  statusText.textContent = 'Analysis complete. Loading dashboard...';

  setTimeout(() => {
    progressContainer.classList.add('hidden');
    hideStepTracker();
    loadReportData(report);
  }, 500);
}

/**
 * Reset the upload view after a failed/aborted run.
 */
function resetUploadUI() {
  const dropzone = document.getElementById('dropzone');
  const progressContainer = document.getElementById('upload-progress-container');
  const progressFill = document.getElementById('progress-fill');
  progressContainer.classList.add('hidden');
  hideStepTracker();
  if (progressFill) progressFill.style.width = '0%';
  dropzone.classList.remove('hidden');
}

/**
 * Reset UI back to upload view
 */
function resetToUploadView() {
  currentReport = null;
  activeTab = 'all';
  activePerspectives = new Set(['all']);

  // Hide dashboard and header buttons
  document.getElementById('dashboard-content').classList.add('hidden');
  document.getElementById('home-btn').classList.add('hidden');
  document.getElementById('download-report-btn').classList.add('hidden');
  document.getElementById('view-debate-btn').classList.add('hidden');
  closeDebateModal();
  document.getElementById('demo-load-btn').classList.remove('hidden');

  // Show upload section
  const uploadSection = document.getElementById('upload-section');
  uploadSection.classList.remove('hidden');
  document.getElementById('dropzone').classList.remove('hidden');
  document.getElementById('upload-progress-container').classList.add('hidden');

  // Reset file input
  document.getElementById('file-input').value = '';

  // Reset perspective filters
  document.querySelectorAll('.perspective-toggle').forEach(btn => {
    btn.classList.remove('active');
  });
  document.getElementById('filter-all').classList.add('active');

  // Reset tab state
  document.querySelectorAll('.tab-btn').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  document.getElementById('tab-all').classList.add('active');
  document.getElementById('tab-all').setAttribute('aria-selected', 'true');
  document.querySelectorAll('.tab-panel-content').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-findings').classList.remove('hidden');
}

/**
 * Initialize Dashboard Tab Bar Actions
 */
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Deactivate other tabs
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });

      // Activate clicked tab
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      const targetPanelId = tab.getAttribute('aria-controls');

      // Hide all panels
      panels.forEach(p => p.classList.add('hidden'));

      // Show selected panel
      document.getElementById(targetPanelId).classList.remove('hidden');

      // Update state
      if (tab.id === 'tab-all') {
        activeTab = 'all';
        renderFindingsList();
      } else if (tab.id === 'tab-high') {
        activeTab = 'high';
        renderFindingsList();
      } else if (tab.id === 'tab-contested') {
        activeTab = 'contested';
      } else if (tab.id === 'tab-secrets') {
        activeTab = 'secrets';
      } else if (tab.id === 'tab-ledger') {
        activeTab = 'ledger';
      }
    });
  });
}

/**
 * Initialize Perspective Filter Toggle Buttons
 */
function initPerspectiveFilters() {
  const toggles = document.querySelectorAll('.perspective-toggle');

  toggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
      const perspective = toggle.dataset.perspective;

      if (perspective === 'all') {
        // "All" resets everything
        activePerspectives = new Set(['all']);
        toggles.forEach(t => t.classList.remove('active'));
        toggle.classList.add('active');
      } else {
        // Individual toggle  remove "all"
        activePerspectives.delete('all');
        document.getElementById('filter-all').classList.remove('active');

        if (activePerspectives.has(perspective)) {
          activePerspectives.delete(perspective);
          toggle.classList.remove('active');
        } else {
          activePerspectives.add(perspective);
          toggle.classList.add('active');
        }

        // If nothing selected, revert to "all"
        if (activePerspectives.size === 0) {
          activePerspectives = new Set(['all']);
          document.getElementById('filter-all').classList.add('active');
        }
      }

      renderFindingsList();
    });
  });
}

/**
 * Check if a finding matches the active perspective filters
 */
function matchesPerspectiveFilter(finding) {
  if (activePerspectives.has('all')) return true;

  // Map source_agent to filter perspective
  if (finding.source_agent === 'preflight_secret_gate') {
    return activePerspectives.has('preflight');
  }
  if (finding.perspective === 'blast_radius') {
    return activePerspectives.has('blast_radius');
  }
  // correctness and security map directly
  return activePerspectives.has(finding.perspective);
}

/**
 * Load complete report structure into dashboard memory and redraw
 * @param {Object} report
 */
function loadReportData(report) {
  currentReport = report;

  // Hide upload section, show dashboard
  document.getElementById('upload-section').classList.add('hidden');
  document.getElementById('dashboard-content').classList.remove('hidden');

  // Show header buttons
  document.getElementById('home-btn').classList.remove('hidden');
  document.getElementById('download-report-btn').classList.remove('hidden');
  document.getElementById('demo-load-btn').classList.add('hidden');

  // Reveal the debate replay button only when a transcript was actually recorded.
  const debateBtn = document.getElementById('view-debate-btn');
  debateBtn.classList.toggle('hidden', !getDebateTranscript(report));

  // 1. Populate Scan Info
  document.getElementById('meta-time').textContent = report.run_metadata.start_time ? formatTimestamp(report.run_metadata.start_time) : 'n/a';
  const compilationMode = report.run_metadata.compilation_mode || 'unknown';
  const compilationEl = document.getElementById('meta-compilation');
  // The "coordinated" path means the ADK-driven coordinator compiled the report;
  // surface that as "ADK" rather than the opaque internal mode name.
  compilationEl.textContent = compilationMode === 'coordinated' ? 'ADK' : compilationMode === 'terminal_fallback' ? 'Terminal Fallback' : compilationMode;
  compilationEl.className = 'meta-value' + (compilationMode === 'terminal_fallback' ? ' compilation-fallback' : ' compilation-ok');

  // 2. Populate Corpus Summary
  document.getElementById('stat-file-count').textContent = report.corpus_summary.file_count || 0;
  document.getElementById('stat-total-bytes').textContent = formatBytes(report.corpus_summary.total_bytes || 0);
  document.getElementById('stat-skipped-count').textContent = report.corpus_summary.skipped_files || 0;

  // Populate skipped logs list if detailed log is present
  const skippedCard = document.getElementById('skipped-files-list');
  const skippedUl = document.getElementById('skipped-list-ul');
  skippedUl.innerHTML = '';

  if (report.corpus_summary.skipped_log && Object.keys(report.corpus_summary.skipped_log).length > 0) {
    skippedCard.classList.remove('hidden');
    Object.entries(report.corpus_summary.skipped_log).forEach(([filepath, entry]) => {
      const li = document.createElement('li');
      li.textContent = `${filepath}: ${entry.skipped_reason}`;
      skippedUl.appendChild(li);
    });
  } else {
    skippedCard.classList.add('hidden');
  }

  // 3. System Perspectives & Gate Badges
  updatePerspectiveBadge('badge-gate-status', report.gate_status?.status || 'complete');

  const perspectives = {};
  if (report.perspective_statuses) {
    report.perspective_statuses.forEach(p => {
      perspectives[p.perspective] = p;
    });
  }

  updatePerspectiveBadge('badge-correctness-status', perspectives['correctness']?.status || 'skipped');
  updatePerspectiveBadge('badge-security-status', perspectives['security']?.status || 'skipped');
  updatePerspectiveBadge('badge-blast-radius-status', perspectives['blast_radius']?.status || 'disabled');

  // 4. Severity Counter Badges
  const counts = report.severity_counts || {};
  document.getElementById('count-critical').textContent = counts.critical || 0;
  document.getElementById('count-high').textContent = counts.high || 0;
  document.getElementById('count-medium').textContent = counts.medium || 0;
  document.getElementById('count-low').textContent = counts.low || 0;
  document.getElementById('count-info').textContent = counts.info || 0;

  // Render warnings if validator raised warnings
  const warningsBanner = document.getElementById('validator-warning-banner');
  const warningsUl = document.getElementById('warnings-list-ul');
  warningsUl.innerHTML = '';
  if (report.validator_warnings && report.validator_warnings.length > 0) {
    warningsBanner.classList.remove('hidden');
    report.validator_warnings.forEach(warn => {
      const li = document.createElement('li');
      li.textContent = warn;
      warningsUl.appendChild(li);
    });
  } else {
    warningsBanner.classList.add('hidden');
  }

  document.getElementById('tab-count-findings').textContent = (report.findings || []).length;

  const highCriticalCount = (report.high_critical_findings || []).length;
  document.getElementById('tab-count-high').textContent = highCriticalCount;

  document.getElementById('tab-count-contested').textContent = (report.contested_items || []).length;
  document.getElementById('tab-count-secrets').textContent = (report.secret_scan_summary || []).length;

  // 6. Draw main lists
  renderFindingsList();
  renderContestedList();
  renderSecretsList();
  renderLedgerList();
}

/**
 * Render standard findings list using DOM template builders
 */
function renderFindingsList() {
  const container = document.getElementById('findings-list');
  container.innerHTML = '';

  if (!currentReport || !currentReport.findings) return;

  // Filter findings based on active tab and perspective selection
  let filtered = currentReport.findings;

  if (activeTab === 'high') {
    filtered = currentReport.high_critical_findings || [];
  }

  // Apply perspective filter
  filtered = filtered.filter(f => matchesPerspectiveFilter(f));

  if (filtered.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No findings matching the current filters.</p>';
    return;
  }

  filtered.forEach(finding => {
    container.appendChild(createFindingCardDOM(finding));
  });
}

/**
 * Render contested findings list
 */
function renderContestedList() {
  const container = document.getElementById('contested-list');
  container.innerHTML = '';

  if (!currentReport || !currentReport.contested_items || currentReport.contested_items.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No contested items in this report.</p>';
    return;
  }

  currentReport.contested_items.forEach(finding => {
    container.appendChild(createFindingCardDOM(finding));
  });
}

/**
 * Render secret gate findings inside the table layout
 */
function renderSecretsList() {
  const tbody = document.getElementById('secrets-table-body');
  tbody.innerHTML = '';

  if (!currentReport || !currentReport.secret_scan_summary || currentReport.secret_scan_summary.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="table-placeholder">No credentials detected in the codebase.</td>
      </tr>`;
    return;
  }

  currentReport.secret_scan_summary.forEach(secret => {
    const tr = document.createElement('tr');

    // Type cell
    const tdType = document.createElement('td');
    tdType.innerHTML = `<strong>${escapeHtml(secret.secret_type)}</strong>`;
    tr.appendChild(tdType);

    // Location cell
    const tdLoc = document.createElement('td');
    tdLoc.className = 'loc-cell';
    tdLoc.textContent = `${secret.location.path} : Line ${secret.location.line_start}`;
    tr.appendChild(tdLoc);

    // Severity cell
    const tdSev = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `finding-severity-badge ${secret.severity}`;
    badge.textContent = secret.severity;
    tdSev.appendChild(badge);
    tr.appendChild(tdSev);

    // Exposure status
    const tdExposure = document.createElement('td');
    const exposureLabel = document.createElement('span');
    exposureLabel.className = secret.exposure_status === 'prompt_exposed' ? 'highlight-text' : 'muted-text';
    exposureLabel.textContent = secret.exposure_status;
    tdExposure.appendChild(exposureLabel);
    tr.appendChild(tdExposure);

    // Fingerprint (salted-hash only)
    const tdFingerprint = document.createElement('td');
    tdFingerprint.style.fontFamily = 'var(--font-mono)';
    tdFingerprint.style.fontSize = '0.75rem';
    tdFingerprint.textContent = secret.fingerprint;
    tr.appendChild(tdFingerprint);

    tbody.appendChild(tr);
  });
}

/**
 * Render the details of the conservation/accounting ledger
 */
function renderLedgerList() {
  if (!currentReport || !currentReport.accounting_ledger) return;

  const ledger = currentReport.accounting_ledger;

  document.getElementById('ledger-count-included').textContent = (ledger.included || []).length;
  document.getElementById('ledger-count-merged').textContent = (ledger.merged || []).length;
  document.getElementById('ledger-count-omitted').textContent = (ledger.omitted || []).length;
  document.getElementById('ledger-count-contested').textContent = (ledger.contested || []).length;

  populateLedgerUl('ledger-list-included', ledger.included || []);
  populateLedgerUl('ledger-list-contested', ledger.contested || []);

  // Custom renderer for Merged ledger entries showing parent-child maps
  const mergedUl = document.getElementById('ledger-list-merged');
  mergedUl.innerHTML = '';
  if (ledger.merged && ledger.merged.length > 0) {
    ledger.merged.forEach(entry => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div>
          <strong>Output:</strong> ${escapeHtml(shortId(entry.output_id))}
          <div style="font-size: 0.65rem; color: var(--text-secondary); margin-top: 0.25rem;">
            From inputs: ${escapeHtml(entry.input_ids.map(shortId).join(', '))}
          </div>
        </div>`;
      mergedUl.appendChild(li);
    });
  } else {
    mergedUl.innerHTML = '<li class="table-placeholder">No merged items.</li>';
  }

  // Custom renderer for Omitted ledger entries showing reasons
  const omittedUl = document.getElementById('ledger-list-omitted');
  omittedUl.innerHTML = '';
  if (ledger.omitted && ledger.omitted.length > 0) {
    ledger.omitted.forEach(entry => {
      const li = document.createElement('li');
      li.style.flexDirection = 'column';
      li.style.alignItems = 'flex-start';
      li.innerHTML = `
        <strong>${escapeHtml(shortId(entry.id))}</strong>
        <span class="ledger-omit-reason">${escapeHtml(entry.reason)}</span>`;
      omittedUl.appendChild(li);
    });
  } else {
    omittedUl.innerHTML = '<li class="table-placeholder">No omitted items.</li>';
  }
}

/**
 * Helper to populate basic list of IDs into ledger card ULs
 */
function populateLedgerUl(elementId, idList) {
  const ul = document.getElementById(elementId);
  ul.innerHTML = '';

  if (idList.length === 0) {
    ul.innerHTML = '<li class="table-placeholder">No items.</li>';
    return;
  }

  idList.forEach(id => {
    const li = document.createElement('li');
    li.textContent = shortId(id);
    ul.appendChild(li);
  });
}

/**
 * Builder creating finding item cards dynamically with events
 * @param {Object} finding
 * @returns {HTMLElement}
 */
function createFindingCardDOM(finding) {
  const card = document.createElement('div');
  card.className = 'finding-card';
  card.id = `finding-node-${finding.id}`;

  const summary = document.createElement('div');
  summary.className = 'finding-summary';

  const badge = document.createElement('span');
  badge.className = `finding-severity-badge ${finding.severity}`;
  badge.textContent = finding.severity;
  summary.appendChild(badge);

  const meta = document.createElement('div');
  meta.className = 'finding-meta';

  const title = document.createElement('span');
  title.className = 'finding-title';
  title.textContent = finding.claim;
  meta.appendChild(title);

  const loc = document.createElement('span');
  loc.className = 'finding-loc';
  loc.textContent = `${finding.location.path} : Lines ${finding.location.line_start} - ${finding.location.line_end}`;
  meta.appendChild(loc);

  const src = document.createElement('span');
  src.className = 'finding-source';
  src.innerHTML = `Detected by: <span>${escapeHtml(finding.source_agent)}</span> (Perspective: <span>${escapeHtml(finding.perspective)}</span>)`;
  meta.appendChild(src);

  summary.appendChild(meta);

  const expander = document.createElement('div');
  expander.className = 'finding-expand-indicator';
  expander.textContent = 'v';
  summary.appendChild(expander);

  card.appendChild(summary);

  // Hidden details container
  const details = document.createElement('div');
  details.className = 'finding-details hidden';

  // ID Section
  const idSec = document.createElement('div');
  idSec.className = 'detail-section';
  idSec.innerHTML = `<h4>Stable Finding ID</h4><p style="font-family: var(--font-mono); font-size: 0.75rem;">${escapeHtml(finding.id)}</p>`;
  details.appendChild(idSec);

  // Next Actions Section
  if (finding.recommended_next_action) {
    const actionSec = document.createElement('div');
    actionSec.className = 'detail-section';
    actionSec.innerHTML = `<h4>Recommended Remediation</h4><p>${escapeHtml(finding.recommended_next_action)}</p>`;
    details.appendChild(actionSec);
  }

  // Evidence refs section
  if (finding.evidence_ref && finding.evidence_ref.length > 0) {
    const evidenceSec = document.createElement('div');
    evidenceSec.className = 'detail-section';
    evidenceSec.innerHTML = '<h4>Grounded Evidence references</h4>';

    const pillContainer = document.createElement('div');
    pillContainer.className = 'evidence-pill-container';
    finding.evidence_ref.forEach(ref => {
      const pill = document.createElement('span');
      pill.className = 'evidence-pill';
      pill.textContent = ref;
      pillContainer.appendChild(pill);
    });

    evidenceSec.appendChild(pillContainer);
    details.appendChild(evidenceSec);
  }

  // Merged constituents section
  if (finding.merged_from && finding.merged_from.length > 0) {
    const mergedSec = document.createElement('div');
    mergedSec.className = 'detail-section';
    mergedSec.innerHTML = '<h4>Merged Constituent findings</h4>';

    const tagContainer = document.createElement('div');
    tagContainer.className = 'merged-id-list';
    finding.merged_from.forEach(mId => {
      const tag = document.createElement('span');
      tag.className = 'merged-id-tag';
      tag.textContent = shortId(mId);
      tag.title = mId;
      tagContainer.appendChild(tag);
    });

    mergedSec.appendChild(tagContainer);
    details.appendChild(mergedSec);
  }

  card.appendChild(details);

  // Toggle expand event
  summary.addEventListener('click', () => {
    const isExpanded = card.classList.toggle('expanded');
    details.classList.toggle('hidden');
    expander.textContent = isExpanded ? '^' : 'v';
  });

  return card;
}

/* --------------------------------------------------------------------------- *
 * Adversarial debate viewer — replays the redaction-safe back-and-forth between
 * Claude (challenger) and Gemini (defender) that decided each security finding.
 * --------------------------------------------------------------------------- */

function openDebateModal() {
  const transcript = getDebateTranscript(currentReport);
  if (!transcript) return;
  renderDebateTranscript(transcript);
  const modal = document.getElementById('debate-modal');
  modal.classList.remove('hidden');
  document.body.classList.add('modal-open');
}

function closeDebateModal() {
  const modal = document.getElementById('debate-modal');
  if (modal) modal.classList.add('hidden');
  document.body.classList.remove('modal-open');
}

const RESOLUTION_META = {
  survived: { label: 'KEPT', cls: 'res-survived' },
  contested: { label: 'CONTESTED', cls: 'res-contested' },
  defeated: { label: 'DROPPED', cls: 'res-defeated' },
};

/**
 * Render the transcript (meta strip + per-round exchange + final resolutions)
 * into the modal. All text is treated as untrusted and HTML-escaped.
 */
function renderDebateTranscript(t) {
  const meta = document.getElementById('debate-modal-meta');
  const fs = t.final_score || {};
  const metaBits = [
    `<span class="debate-meta-pill">${t.seed_findings || 0} seed finding(s)</span>`,
    `<span class="debate-meta-pill">${(t.rounds || []).length} round(s)</span>`,
    `<span class="debate-meta-pill">final score — challenger ${fs.challenger ?? '0'} · defender ${fs.defender ?? '0'}</span>`,
  ];
  if (t.stop_reason) {
    metaBits.push(`<span class="debate-meta-pill">stop: ${escapeHtml(String(t.stop_reason))}</span>`);
  }
  meta.innerHTML = metaBits.join('');

  const body = document.getElementById('debate-modal-body');
  body.innerHTML = '';

  (t.rounds || []).forEach(round => {
    const roundEl = document.createElement('div');
    roundEl.className = 'debate-round';

    const head = document.createElement('div');
    head.className = 'debate-round-head';
    let scoreLine = '';
    const sb = (t.scoreboard || []).find(s => s.round === round.round);
    if (sb) scoreLine = ` <span class="debate-round-score">challenger ${sb.challenger} · defender ${sb.defender}</span>`;
    head.innerHTML = `Round ${round.round}${scoreLine}`;
    roundEl.appendChild(head);

    (round.messages || []).forEach(msg => {
      const isDefender = msg.role === 'defender';
      const isSystem = msg.role === 'system';
      const row = document.createElement('div');
      row.className = 'debate-msg ' + (isSystem ? 'is-system' : isDefender ? 'is-defender' : 'is-challenger');

      const who = document.createElement('span');
      who.className = 'debate-msg-actor';
      who.textContent = isSystem ? 'system' : isDefender ? 'Gemini · defender' : 'Claude · challenger';

      const text = document.createElement('span');
      text.className = 'debate-msg-text';
      text.textContent = msg.message;

      row.appendChild(who);
      row.appendChild(text);
      roundEl.appendChild(row);
    });

    body.appendChild(roundEl);
  });

  // Final resolutions block — how each finding ended up.
  if (t.resolutions && t.resolutions.length > 0) {
    const resWrap = document.createElement('div');
    resWrap.className = 'debate-resolutions';
    const h = document.createElement('h3');
    h.textContent = 'How each finding was resolved';
    resWrap.appendChild(h);

    t.resolutions.forEach(r => {
      const rm = RESOLUTION_META[r.resolution] || { label: (r.resolution || '').toUpperCase(), cls: '' };
      const item = document.createElement('div');
      item.className = 'debate-resolution-item';

      const badge = document.createElement('span');
      badge.className = `debate-res-badge ${rm.cls}`;
      badge.textContent = rm.label;

      const claim = document.createElement('div');
      claim.className = 'debate-res-claim';
      claim.innerHTML = `<span class="debate-res-sev sev-${escapeHtml(r.severity || 'info')}">${escapeHtml(r.severity || 'info')}</span> ${escapeHtml(r.claim || '')}`;

      item.appendChild(badge);
      item.appendChild(claim);

      if (r.closed_reason) {
        const reason = document.createElement('div');
        reason.className = 'debate-res-reason';
        reason.textContent = r.closed_reason;
        claim.appendChild(reason);
      }

      resWrap.appendChild(item);
    });

    body.appendChild(resWrap);
  }
}

/**
 * Generate and download a clean portable Markdown report
 */
function downloadReport() {
  if (!currentReport) return;

  const report = currentReport;
  const timestamp = report.run_metadata.start_time
    ? new Date(report.run_metadata.start_time).toLocaleString()
    : 'Unknown';
  const compilationMode = report.run_metadata.compilation_mode || 'unknown';
  const counts = report.severity_counts || {};

  let md = '';

  // Header
  md += '# Code Review Report\n\n';
  const coordinatorLabel = compilationMode === 'coordinated' ? 'ADK' : compilationMode === 'terminal_fallback' ? 'Terminal Fallback' : compilationMode;
  md += `**Generated:** ${timestamp}  \n`;
  md += `**Coordinator:** ${coordinatorLabel}  \n`;
  md += `**Run ID:** ${report.run_metadata.run_id || 'N/A'}  \n\n`;

  // Executive Summary
  md += '---\n\n';
  md += '## Executive Summary\n\n';

  const totalFindings = (report.findings || []).length;
  const totalContested = (report.contested_items || []).length;
  const totalSecrets = (report.secret_scan_summary || []).length;

  md += `| Metric | Count |\n`;
  md += `|--------|-------|\n`;
  md += `| Active Findings | ${totalFindings} |\n`;
  md += `| Contested Items | ${totalContested} |\n`;
  md += `| Secrets Detected | ${totalSecrets} |\n\n`;

  md += `### Severity Breakdown\n\n`;
  md += `| Severity | Count |\n`;
  md += `|----------|-------|\n`;
  md += `|  Critical | ${counts.critical || 0} |\n`;
  md += `|  High | ${counts.high || 0} |\n`;
  md += `|  Medium | ${counts.medium || 0} |\n`;
  md += `|  Low | ${counts.low || 0} |\n`;
  md += `|  Info | ${counts.info || 0} |\n\n`;

  // Agent Statuses
  md += '### Agent Perspective Statuses\n\n';
  md += '| Agent | Status | Details |\n';
  md += '|-------|--------|--------|\n';
  md += `| Pre-Flight Gate | ${report.gate_status?.status || 'N/A'} | ${report.gate_status?.reason || ''} |\n`;
  if (report.perspective_statuses) {
    report.perspective_statuses.forEach(p => {
      const name = p.perspective === 'correctness' ? 'Correctness Agent'
                 : p.perspective === 'security' ? 'Security Agent'
                 : p.perspective === 'blast_radius' ? 'Blast-Radius (Orbit)'
                 : p.perspective;
      md += `| ${name} | ${p.status} | ${p.reason || ''} |\n`;
    });
  }
  md += '\n';

  // Findings
  md += '---\n\n';
  md += '## Active Findings\n\n';

  if (report.findings && report.findings.length > 0) {
    // Group by perspective
    const grouped = {};
    report.findings.forEach(f => {
      const key = f.source_agent === 'preflight_secret_gate' ? 'Pre-Flight Gate'
                : f.perspective === 'correctness' ? 'Correctness'
                : f.perspective === 'security' ? 'Security'
                : f.perspective === 'blast_radius' ? 'Blast-Radius (Orbit)'
                : f.perspective;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(f);
    });

    for (const [group, findings] of Object.entries(grouped)) {
      md += `### ${group}\n\n`;
      findings.forEach(f => {
        md += `#### \\[${f.severity.toUpperCase()}\\] ${f.claim}\n\n`;
        md += `- **Location:** \`${f.location.path}\` lines ${f.location.line_start}-${f.location.line_end}\n`;
        md += `- **Source Agent:** ${f.source_agent}\n`;
        md += `- **Finding ID:** \`${f.id}\`\n`;
        if (f.evidence_ref && f.evidence_ref.length > 0) {
          md += `- **Evidence:** ${f.evidence_ref.map(r => '`' + r + '`').join(', ')}\n`;
        }
        if (f.recommended_next_action) {
          md += `- **Recommended Action:** ${f.recommended_next_action}\n`;
        }
        if (f.merged_from && f.merged_from.length > 0) {
          md += `- **Merged From:** ${f.merged_from.map(id => '`' + id + '`').join(', ')}\n`;
        }
        md += '\n';
      });
    }
  } else {
    md += '*No active findings.*\n\n';
  }

  // Contested
  if (report.contested_items && report.contested_items.length > 0) {
    md += '---\n\n';
    md += '## Contested Items\n\n';
    report.contested_items.forEach(f => {
      md += `#### \\[${f.severity.toUpperCase()}\\] ${f.claim}\n\n`;
      md += `- **Location:** \`${f.location.path}\` lines ${f.location.line_start}-${f.location.line_end}\n`;
      md += `- **Source Agent:** ${f.source_agent}\n`;
      if (f.recommended_next_action) {
        md += `- **Note:** ${f.recommended_next_action}\n`;
      }
      md += '\n';
    });
  }

  // Secret Scan
  if (report.secret_scan_summary && report.secret_scan_summary.length > 0) {
    md += '---\n\n';
    md += '## Secret Scan Summary\n\n';
    md += '| Type | Location | Severity | Exposure | Fingerprint |\n';
    md += '|------|----------|----------|----------|-------------|\n';
    report.secret_scan_summary.forEach(s => {
      md += `| ${s.secret_type} | ${s.location.path}:${s.location.line_start} | ${s.severity} | ${s.exposure_status} | \`${s.fingerprint}\` |\n`;
    });
    md += '\n';
  }

  // Conservation Ledger
  if (report.accounting_ledger) {
    md += '---\n\n';
    md += '## Conservation Ledger\n\n';
    const l = report.accounting_ledger;
    md += `- **Included:** ${(l.included || []).length} findings\n`;
    md += `- **Merged:** ${(l.merged || []).length} consolidations\n`;
    md += `- **Omitted:** ${(l.omitted || []).length} suppressions\n`;
    md += `- **Contested:** ${(l.contested || []).length} items\n\n`;

    md += `*Integrity: Inputs == Included U Merged U Omitted U Contested (validator enforced)*\n\n`;
  }

  // Adversarial Security Debate
  const transcript = getDebateTranscript(report);
  if (transcript) {
    md += '---\n\n';
    md += '## Adversarial Security Debate\n\n';
    md += 'Claude (challenger / security hawk) vs Gemini (defender / ship-it advocate). ';
    md += 'This is the redaction-safe back-and-forth that decided each security finding below.\n\n';

    const fs = transcript.final_score || {};
    md += `- **Seed findings:** ${transcript.seed_findings || 0}\n`;
    md += `- **Rounds:** ${(transcript.rounds || []).length}\n`;
    md += `- **Final score:** challenger ${fs.challenger ?? 0} · defender ${fs.defender ?? 0}\n`;
    if (transcript.stop_reason) md += `- **Stop reason:** ${transcript.stop_reason}\n`;
    md += '\n';

    (transcript.rounds || []).forEach(round => {
      const sb = (transcript.scoreboard || []).find(s => s.round === round.round);
      const scoreNote = sb ? ` _(challenger ${sb.challenger} · defender ${sb.defender})_` : '';
      md += `### Round ${round.round}${scoreNote}\n\n`;
      (round.messages || []).forEach(msg => {
        const actor = msg.role === 'defender' ? 'Gemini (defender)'
                    : msg.role === 'challenger' ? 'Claude (challenger)'
                    : 'system';
        md += `- **${actor}:** ${msg.message}\n`;
      });
      md += '\n';
    });

    if (transcript.resolutions && transcript.resolutions.length > 0) {
      md += '### Resolutions\n\n';
      md += '| Outcome | Severity | Finding | Reasoning |\n';
      md += '|---------|----------|---------|-----------|\n';
      transcript.resolutions.forEach(r => {
        const outcome = r.resolution === 'survived' ? 'KEPT'
                      : r.resolution === 'contested' ? 'CONTESTED'
                      : r.resolution === 'defeated' ? 'DROPPED'
                      : (r.resolution || '');
        const reason = (r.closed_reason || '').replace(/\|/g, '\\|');
        const claim = (r.claim || '').replace(/\|/g, '\\|');
        md += `| ${outcome} | ${r.severity || 'info'} | ${claim} | ${reason} |\n`;
      });
      md += '\n';
    }
  }

  // Validator Warnings
  if (report.validator_warnings && report.validator_warnings.length > 0) {
    md += '---\n\n';
    md += '## Validator Warnings\n\n';
    report.validator_warnings.forEach(w => {
      md += `-  ${w}\n`;
    });
    md += '\n';
  }

  md += '---\n\n';
  md += '*Report generated by GDG-YorkU Code Review Tool - Automated Multi-Agent Integrity Suite*\n';

  // Download
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `code-review-report-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Helpers
 */
function updatePerspectiveBadge(badgeId, statusValue) {
  const badge = document.getElementById(badgeId);
  if (!badge) return;

  badge.className = 'status-badge';
  badge.textContent = statusValue.toUpperCase();

  switch(statusValue.toLowerCase()) {
    case 'complete':
    case 'success':
      badge.classList.add('status-complete');
      break;
    case 'failed':
      badge.classList.add('status-failed');
      break;
    case 'skipped':
    case 'complete_limited':
      badge.classList.add('status-skipped');
      break;
    case 'disabled':
    case 'unavailable':
      badge.classList.add('status-disabled');
      break;
    default:
      badge.classList.add('status-pending');
  }
}

function formatTimestamp(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString();
  } catch(e) {
    return isoStr;
  }
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function shortId(id) {
  if (id.length <= 16) return id;
  return id.substring(0, 8) + '...' + id.substring(id.length - 8);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
