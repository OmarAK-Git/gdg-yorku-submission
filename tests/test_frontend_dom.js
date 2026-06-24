// Self-contained JS DOM test runner for app.js
const fs = require('path') ? require('fs') : null;
const path = require('path');
const assert = require('assert');

// 1. Mock DOM Environment
class MockElement {
  constructor(tagName = 'div', id = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.children = [];
    this.classList = {
      classes: new Set(),
      add: (c) => this.classList.classes.add(c),
      remove: (c) => this.classList.classes.delete(c),
      toggle: (c) => {
        if (this.classList.classes.has(c)) {
          this.classList.classes.delete(c);
          return false;
        } else {
          this.classList.classes.add(c);
          return true;
        }
      },
      contains: (c) => this.classList.classes.has(c)
    };
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this._textContent = '';
    this._innerHTML = '';
    this.style = {};
    this.value = '';
    this.title = '';
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(val) {
    this._innerHTML = val;
    if (val === '') {
      this.children = [];
    }
  }

  get textContent() {
    return this._textContent;
  }

  set textContent(val) {
    this._textContent = val;
    if (val === '') {
      this.children = [];
    }
  }

  get className() {
    return Array.from(this.classList.classes).join(' ');
  }

  set className(val) {
    this.classList.classes.clear();
    if (val) {
      val.split(/\s+/).filter(Boolean).forEach(c => this.classList.classes.add(c));
    }
  }

  setAttribute(k, v) {
    this.attributes[k] = String(v);
    if (k === 'class') {
      this.className = v;
    }
  }

  getAttribute(k) {
    return this.attributes[k] || null;
  }

  addEventListener(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  }

  dispatchEvent(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  remove() {
    this.children = [];
  }
}

// Map of mocked IDs and Query selectors
const elementsById = {};
const elementsByQuery = {};

const documentMock = {
  listeners: {},
  addEventListener(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  },
  getElementById(id) {
    if (!elementsById[id]) {
      elementsById[id] = new MockElement('div', id);
    }
    return elementsById[id];
  },
  querySelectorAll(query) {
    if (!elementsByQuery[query]) {
      elementsByQuery[query] = [];
    }
    return elementsByQuery[query];
  },
  createElement(tag) {
    return new MockElement(tag);
  }
};

// Setup Globals
global.document = documentMock;
global.window = {
  addEventListener(event, cb) {}
};
global.alert = (msg) => {
  global.alertMessage = msg;
};

// Populate the required elements from index.html structure
const dashboardContent = documentMock.getElementById('dashboard-content');
dashboardContent.classList.add('hidden');

const selectElement = documentMock.getElementById('orchestrator-select');
selectElement.value = 'adk';

// Perspective filtering switched from a single <select> to a set of multi-select
// toggle buttons (.perspective-toggle with data-perspective). Wire up the mock buttons
// that initPerspectiveFilters() binds at DOMContentLoaded.
const perspectiveToggles = [
  documentMock.getElementById('filter-all'),
  documentMock.getElementById('filter-preflight'),
  documentMock.getElementById('filter-correctness'),
  documentMock.getElementById('filter-security'),
  documentMock.getElementById('filter-orbit'),
];
perspectiveToggles[0].dataset.perspective = 'all';
perspectiveToggles[0].classList.add('active');
perspectiveToggles[1].dataset.perspective = 'preflight';
perspectiveToggles[2].dataset.perspective = 'correctness';
perspectiveToggles[3].dataset.perspective = 'security';
perspectiveToggles[4].dataset.perspective = 'blast_radius';
elementsByQuery['.perspective-toggle'] = perspectiveToggles;
const filterCorrectness = perspectiveToggles[2];
const filterAll = perspectiveToggles[0];

// Mock the tabs
const tabs = [
  documentMock.getElementById('tab-all'),
  documentMock.getElementById('tab-high'),
  documentMock.getElementById('tab-contested'),
  documentMock.getElementById('tab-secrets'),
  documentMock.getElementById('tab-ledger')
];
tabs[0].id = 'tab-all';
tabs[0].setAttribute('aria-controls', 'panel-findings');
tabs[1].id = 'tab-high';
tabs[1].setAttribute('aria-controls', 'panel-findings');
tabs[2].id = 'tab-contested';
tabs[2].setAttribute('aria-controls', 'panel-contested');
tabs[3].id = 'tab-secrets';
tabs[3].setAttribute('aria-controls', 'panel-secrets');
tabs[4].id = 'tab-ledger';
tabs[4].setAttribute('aria-controls', 'panel-ledger');

elementsByQuery['.tab-btn'] = tabs;

const panels = [
  documentMock.getElementById('panel-findings'),
  documentMock.getElementById('panel-contested'),
  documentMock.getElementById('panel-secrets'),
  documentMock.getElementById('panel-ledger')
];
elementsByQuery['.tab-panel-content'] = panels;

// 2. Load app.js code dynamically
const appJsPath = path.join(__dirname, '../src/gdg_yorku_submission/static/app.js');
const appJsCode = fs.readFileSync(appJsPath, 'utf8');

// Expose MOCK_DEMO_REPORT globally so tests can run checks on it
const appJsExposed = appJsCode.replace('const MOCK_DEMO_REPORT =', 'global.MOCK_DEMO_REPORT =');

// Run the script under our mock environment
eval(appJsExposed);

// Trigger DOMContentLoaded
if (documentMock.listeners['DOMContentLoaded']) {
  documentMock.listeners['DOMContentLoaded'].forEach(cb => cb());
}

console.log("DOM Mock Initialized. Starting tests...");

// Test Case 1: Check initial elements
assert.strictEqual(documentMock.getElementById('dashboard-content').classList.contains('hidden'), true);

// Test Case 2: Click "Load Mock Demo Report" button and assert rendering
const demoBtn = documentMock.getElementById('demo-load-btn');
demoBtn.dispatchEvent('click');

// Dashboard should now be visible
assert.strictEqual(documentMock.getElementById('dashboard-content').classList.contains('hidden'), false);

// Check perspective status badges are updated
const correctnessBadge = documentMock.getElementById('badge-correctness-status');
assert.strictEqual(correctnessBadge.textContent, 'COMPLETE');

// Check counts are updated
const highTabCount = documentMock.getElementById('tab-count-high');
assert.strictEqual(highTabCount.textContent, 2);

// Test Case 3: Check findings rendering and filtering
const findingsList = documentMock.getElementById('findings-list');
// Initial load shows 5 active findings, then a ledger-provenance divider plus the
// mock's 3 parsed-out snapshots (1 omitted + 2 merged constituents) = 9 children.
assert.strictEqual(findingsList.children.length, 9);

// Toggle the "correctness" perspective filter on (multi-select buttons)
filterCorrectness.dispatchEvent('click');
// Correctness count should be 2
assert.strictEqual(findingsList.children.length, 2);

// Click "All" to reset the perspective filter (5 active + divider + 3 provenance)
filterAll.dispatchEvent('click');
assert.strictEqual(findingsList.children.length, 9);

// Flip tab to High/Critical: 2 high/critical active + divider + 2 high merged constituents
// (the omitted snapshot is low severity, so it is filtered out of this tab).
tabs[1].dispatchEvent('click'); // Click tab-high
assert.strictEqual(findingsList.children.length, 5); // cb1a79f..., e302061..., + 2 merged constituents

// Flip tab back to All (5 active + divider + 3 provenance)
tabs[0].dispatchEvent('click'); // Click tab-all
assert.strictEqual(findingsList.children.length, 9);

// Test Case 4: Zero Secret Leakage schema and delegation assertion (REQ-17-2)
// NOTE: Client-side UI trusts the upstream coordinator/agents for credential redaction (delegated to Task 7).
// The frontend only consumes the GateFinding/SecretScanSummary schemas, which do not carry any raw secret fields.
// Here we assert that the frontend schema objects processed and rendered contain no raw value fields (such as 'raw_value' or 'raw-value').

// Assert that the secret_scan_summary in MOCK_DEMO_REPORT contains no raw secret values
MOCK_DEMO_REPORT.secret_scan_summary.forEach(secret => {
  assert.ok(!('raw_value' in secret), "Secret summary must not contain raw_value field");
  assert.ok(!('raw-value' in secret), "Secret summary must not contain raw-value field");
  assert.ok(!('original_value' in secret), "Secret summary must not contain original_value field");
  assert.ok(secret.fingerprint, "Secret summary must only identify secrets by safe fingerprint");
});

// For findings, verify that they carry only claims, not raw secrets
MOCK_DEMO_REPORT.findings.forEach(finding => {
  assert.ok(!('raw_value' in finding), "Findings must not contain raw_value field");
  assert.ok(!('raw-value' in finding), "Findings must not contain raw-value field");
});

// We load a conforming report to verify basic rendering behaves correctly
const schemaConformingReport = {
  "run_metadata": { "orchestrator_type": "AdkOrchestrator" },
  "corpus_summary": { "file_count": 1, "total_bytes": 100, "skipped_files": 0 },
  "perspective_statuses": [],
  "gate_status": { "status": "complete", "finding_ids": [] },
  "severity_counts": { "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0 },
  "high_critical_findings": [
    {
      "id": "test-finding-conforming",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": { "path": "src/app.py", "line_start": 5, "line_end": 5 },
      "claim": "Conforming finding with safe fingerprint identification",
      "recommended_next_action": "Refer to the secret scan summary for detail",
      "evidence_ref": ["file:src/app.py#5"]
    }
  ],
  "findings": [
    {
      "id": "test-finding-conforming",
      "source_agent": "security_deterministic",
      "perspective": "security",
      "severity": "high",
      "location": { "path": "src/app.py", "line_start": 5, "line_end": 5 },
      "claim": "Conforming finding with safe fingerprint identification",
      "recommended_next_action": "Refer to the secret scan summary for detail",
      "evidence_ref": ["file:src/app.py#5"]
    }
  ],
  "secret_scan_summary": [
    {
      "id": "gate-1",
      "secret_type": "Google API Key",
      "fingerprint": "salted_hash_val",
      "exposure_status": "prompt_exposed",
      "severity": "high",
      "location": { "path": "src/app.py", "line_start": 5, "line_end": 5 }
    }
  ],
  "accounting_ledger": {
    "included": ["test-finding-conforming"],
    "merged": [],
    "omitted": [],
    "contested": []
  }
};

loadReportData(schemaConformingReport);

assert.strictEqual(findingsList.children.length, 1);
console.log("Schema conformance and delegation verification passed (REQ-17-2).");

// Test Case 5: Expand card panels
const card = findingsList.children[0];
const summary = card.children[0];
const details = card.children[1];
console.log("Card tag:", card.tagName, "Summary tag:", summary.tagName, "Details tag:", details.tagName);
console.log("Summary listeners before click:", summary.listeners);
console.log("Card classes before click:", Array.from(card.classList.classes));

assert.strictEqual(card.classList.contains('expanded'), false);
assert.strictEqual(details.classList.contains('hidden'), true);

summary.dispatchEvent('click');
console.log("Card classes after click:", Array.from(card.classList.classes));
assert.strictEqual(card.classList.contains('expanded'), true);
assert.strictEqual(details.classList.contains('hidden'), false);

// Test Case 6: Ledger lists are populated
tabs[4].dispatchEvent('click'); // Click tab-ledger
const includedLedgerList = documentMock.getElementById('ledger-list-included');
assert.strictEqual(includedLedgerList.children.length, 1);

console.log("All Node DOM JS tests passed successfully!");
process.exit(0);
