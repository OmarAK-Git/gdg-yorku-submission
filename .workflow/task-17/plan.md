# Workflow Plan - Task 17 (Frontend Report Viewer)

## Goal
Build and verify the frontend components under `src/gdg_yorku_submission/static/` and integrate them with the FastAPI application to display review findings, perspective statuses, severity counters, secret scan results, and the conservation ledger, ensuring no raw secrets are leaked.

## Scope

### In scope
- Create `src/gdg_yorku_submission/static/index.html` as the main dashboard frame.
- Create `src/gdg_yorku_submission/static/styles.css` with a premium dark-mode theme.
- Create `src/gdg_yorku_submission/static/app.js` with drag-and-drop file uploads and dynamically rendered dashboard components.
- Modify `src/gdg_yorku_submission/app.py` to serve the static assets and redirect `/ui` requests.
- Implement unit tests verifying the static file mounts.

### Out of scope
- Live stream debate rendering via Crucible SSE (Task 20/21 upgrades).
- Interactive editing or mutation of findings via the UI (read-only viewer of the compiled report).

## Requirements
| ID | Requirement |
|---|---|
| REQ-17-1 | **UI Core Elements**: Renders upload form, perspective statuses, gate status, severity counts, findings list, contested findings, secret scan summary, and the accounting ledger. |
| REQ-17-2 | **Secret Redaction Check**: Zero raw secret leakage in UI payload. Delegated to the Task 7 pre-flight redaction invariant, which redacts secrets before model/compilation phase. Verified by API test assertions against raw literals. |
| REQ-17-3 | **Static Mounting**: FastAPI serves the application files from `src/gdg_yorku_submission/static/` under `/static/` and mounts a `/ui` redirection. |
| REQ-17-4 | **Dashboard Filtering**: Allow filtering findings by severity level (Critical/High) and perspective. |

## Acceptance Criteria
| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-17-1 | REQ-17-1 | UI displays all sections of the `ReviewReport` schema from a mock or real upload. |
| AC-17-2 | REQ-17-2 | No raw secret literals (e.g. Google API Keys, database passwords) are returned in the `/review` JSON response. Verified via `test_review_upload_with_secrets` in `test_api_skeleton.py` and `test_demo_e2e_run` in `test_demo_sample.py`. |
| AC-17-3 | REQ-17-3 | Fetching `/static/index.html` or `/ui` returns the valid dashboard index page. |
| AC-17-4 | REQ-17-4 | Clicking dashboard filters updates the displayed list of findings dynamically. |

## Implementation Plan
| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-17-1 | Initialize Static Directory and HTML skeleton | `src/gdg_yorku_submission/static/index.html` | pending |
| TASK-17-2 | Write Styling system (styles.css) | `src/gdg_yorku_submission/static/styles.css` | pending |
| TASK-17-3 | Write JS handler for upload & DOM population | `src/gdg_yorku_submission/static/app.js` | pending |
| TASK-17-4 | Mount static routes in FastAPI app | `src/gdg_yorku_submission/app.py` | pending |
| TASK-17-5 | Write route tests for static assets | `tests/test_frontend.py` | pending |
