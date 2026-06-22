// Mock Report Data for manual demo showcase and testing without live server uploads
const MOCK_DEMO_REPORT = {
  "run_metadata": {
    "orchestrator_type": "AdkOrchestrator",
    "start_time": "2026-06-21T17:30:15.123-04:00",
    "duration_ms": 2345,
    "budget_remaining": "85.2% token allocation"
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
      "reason": "AST baseline completed. Debate skipped due to budget lease limit.",
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

document.addEventListener('DOMContentLoaded', () => {
  initDragAndDrop();
  initTabs();
  initFilters();
  
  // Set up mock button handler
  const demoBtn = document.getElementById('demo-load-btn');
  demoBtn.addEventListener('click', () => {
    loadReportData(MOCK_DEMO_REPORT);
  });
});

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
 * Send zip archive to FastAPI backend for analysis
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
  const orchestratorSelect = document.getElementById('orchestrator-select');

  // Transition UI to progress view
  dropzone.classList.add('hidden');
  progressContainer.classList.remove('hidden');
  progressFill.style.width = '20%';
  statusText.textContent = 'Uploading repository archive...';

  const formData = new FormData();
  formData.append('file', file);

  const mode = orchestratorSelect.value;
  progressFill.style.width = '45%';
  statusText.textContent = `Running multi-agent analysis suite (Mode: ${mode === 'adk' ? 'ADK' : 'In-Process'})...`;

  try {
    const response = await fetch(`/review?orchestrator=${mode}`, {
      method: 'POST',
      body: formData
    });

    progressFill.style.width = '85%';

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Review run aborted or failed.');
    }

    const report = await response.json();
    progressFill.style.width = '100%';
    statusText.textContent = 'Validation constraints passed. Rerouting dashboard...';
    
    setTimeout(() => {
      progressContainer.classList.add('hidden');
      dropzone.classList.remove('hidden');
      loadReportData(report);
    }, 600);

  } catch (error) {
    console.error('Analysis failed:', error);
    alert(`Orchestrator Error: ${error.message}`);
    progressContainer.classList.add('hidden');
    dropzone.classList.remove('hidden');
  }
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
 * Initialize Filter Selection Handlers
 */
function initFilters() {
  const filterPerspective = document.getElementById('filter-perspective');
  filterPerspective.addEventListener('change', () => {
    renderFindingsList();
  });
}

/**
 * Load complete report structure into dashboard memory and redraw
 * @param {Object} report 
 */
function loadReportData(report) {
  currentReport = report;
  
  // Unhide Dashboard Panel
  document.getElementById('dashboard-content').classList.remove('hidden');
  
  // 1. Populate Run Diagnostics
  document.getElementById('meta-time').textContent = report.run_metadata.start_time ? formatTimestamp(report.run_metadata.start_time) : 'n/a';
  document.getElementById('meta-type').textContent = report.run_metadata.orchestrator_type || 'UnknownOrchestrator';
  document.getElementById('meta-budget').textContent = report.run_metadata.budget_remaining || 'n/a';
  
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

  const filterPerspective = document.getElementById('filter-perspective').value;
  
  // Filter findings based on active tab and perspective selection
  let filtered = currentReport.findings;

  if (activeTab === 'high') {
    filtered = currentReport.high_critical_findings || [];
  }

  if (filterPerspective !== 'all') {
    filtered = filtered.filter(f => f.perspective === filterPerspective);
  }

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
  expander.textContent = '▼';
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
    expander.textContent = isExpanded ? '▲' : '▼';
  });

  return card;
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
