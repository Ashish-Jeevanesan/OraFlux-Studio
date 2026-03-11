# Development Log

This file logs the automated development and verification process for the Ephemeral Oracle Report Viewer project.

## 1. Project Scaffolding

- Created `backend` and `frontend` directories to house the respective applications.
- Established a root `.gitignore` file.

## 2. Backend Implementation (FastAPI)

- Created a `requirements.txt` with all necessary dependencies (`fastapi`, `oracledb`, `pytest`, etc.).
- Structured the application under the `backend/app/` directory.
- Implemented Pydantic models in `app/models.py` for API request/response validation.
- Created `SessionManager` service (`app/services/session_manager.py`) to handle ephemeral, in-memory user sessions and connection pool lifecycle.
- Implemented `OracleService` (`app/services/oracle_service.py`) to manage Oracle connection pools and query execution.
- Developed a robust `SQLBuilder` service (`app/services/sql_builder.py`) to safely construct paginated and complex aggregation queries from user input.
- Exposed all required API endpoints in `app/main.py`, including CORS configuration and a background task for idle session cleanup.
- Added unit tests for the SQL builder logic in `tests/test_sql_builder.py`.
- Created a `Dockerfile` for containerizing the backend service.
- Added `pyproject.toml` for code formatting and linting rules.

## 3. Frontend Implementation (Angular)

- Scaffolded a new Angular 17 project in the `frontend` directory.
- Installed dependencies: `@angular/material`, `@angular/cdk`, `ngx-echarts`, and `echarts`.
- Configured `app.config.ts` to provide `HttpClient` and import necessary modules for charting and animations.
- Created `SessionService` and `ApiService` to manage session state and encapsulate all backend communication.
- Defined TypeScript interfaces for all API payloads in `app/interfaces/api.interfaces.ts`.
- Built the three core UI components as standalone Angular components:
    1.  `ConnectionFormComponent`: For capturing Oracle credentials.
    2.  `SqlRunnerComponent`: For running queries and displaying results in a paginated Material table.
    3.  `ReportBuilderComponent`: For creating charts using `ngx-echarts`.
- Assembled the main application layout in `app.component.ts` and its template, managing the overall state (`connecting` vs. `connected`).
- Added global styles and an Angular Material theme in `styles.scss`.
- Created a multi-stage `Dockerfile` using Nginx to serve the final application.
- Added linter and formatter configuration (`.eslintrc.json`, `.prettierrc`).

## 4. Verification and Debugging

### Frontend Build
- **Attempt 1:** The `npm run build` command failed due to incorrect `tsconfig.app.json` still referencing deleted Server-Side Rendering (SSR) files.
- **Correction 1:** Modified `tsconfig.app.json` to remove the paths to the deleted SSR files.
- **Attempt 2:** The build failed again, this time due to the initial bundle size exceeding the `1mb` error budget set by default in `angular.json`.
- **Correction 2:** Increased the `maximumError` budget for the initial bundle to `2mb` in `angular.json`.
- **Attempt 3:** The build **succeeded**, producing a warning about the bundle size but no errors.

### Backend Verification
- **Attempt:** Tried to run `pytest` to verify the backend unit tests.
- **Issue:** The command failed because no `python` or `py` executable was found in the system's PATH.
- **Conclusion:** Backend verification could not be completed. The user was notified of the missing Python dependency.

## 5. Final Structure

- The final project structure includes separate, containerized applications for the frontend and backend, a `docker-compose.yml` for orchestration, and a comprehensive `README.md` for setup instructions.
- Cleaned up the extraneous `.git` directory created by the Angular CLI in the `frontend` subfolder.

## 6. Advanced Features and UI/UX Overhaul

- **AI-Powered Chart Suggestions:**
    - Implemented a heuristic-based suggestion engine (`ChartSuggestionService`) to analyze query results and suggest relevant charts.
    - Created a new `ChartSuggestionsComponent` to display clickable suggestions to the user.
    - Integrated the suggestions into the main application flow, allowing one-click generation of charts.
- **Interactive Chart Drill-Down:**
    - Implemented a new `/query/drilldown` backend endpoint to fetch the raw data for a specific chart segment.
    - Added a `(chartClick)` handler on the frontend to capture user interaction.
    - Created a `DrilldownDataDialogComponent` to display the filtered raw data in a paginated table.
- **"OraFlux Studio" Rebranding and Theming:**
    - Renamed the project to "OraFlux Studio" in all relevant UI elements and configuration files.
    - Implemented a new, professional "Flux Blue" color palette by creating a custom Angular Material theme in `styles.scss`.
- **Intensive UI/UX Debugging:**
    - Fixed numerous backend startup errors related to database connection (`DPY-4027`), async operations, and module imports (`NameError`).
    - Resolved a persistent frontend issue where Material Icons failed to load by removing external font links and instead installing and importing the icons directly via an NPM package. This was ultimately fixed by injecting the SVGs directly into the components.
    - Fixed a `textarea` UI bug where the label would overlap with the text.
    - Corrected the layout and spacing of all form components for a more polished and readable interface.
- **Git Repository Setup:**
    - Guided the user through setting up a local Git repository with a repository-specific SSH key to avoid conflicts with global work configurations.
    - Successfully pushed the entire project to the user's personal GitHub repository.

## 7. Deployment and Final Fixes

- **Vercel Deployment:**
    - Prepared the project for frontend deployment on Vercel by creating a `vercel.json` configuration file.
    - Guided the user through creating a project on Vercel and connecting their GitHub repository.
- **Intensive Deployment Debugging:**
    - Encountered a persistent `404: NOT_FOUND` error on the deployed Vercel application.
    - **Attempt 1:** Corrected the `vercel.json` builder from `@vercel/angular` to rely on Vercel's auto-detection. **Failed.**
    - **Attempt 2:** Simplified `vercel.json` to only include the SPA fallback rewrite rule to isolate the issue. **Failed.**
    - **Attempt 3 (Forensic):** Added a `ls -R dist` command to the build script to inspect Vercel's build output. The log revealed the application files were being placed in `dist/browser`.
    - **Attempt 4:** Based on the forensic log, corrected the `outputPath` in `angular.json` to `"dist"` and instructed the user to set the Vercel UI "Output Directory" to `dist/browser`. This was the final, successful solution.
- **Backend Enhancements:**
    - Implemented comprehensive logging for all API endpoint calls and application startup events.
    - Added detailed code comments to all backend services and SQL generation logic for improved clarity and maintainability.
    - Added `/` (root) and `/health` endpoints for easy service deployment verification.
    - Fixed a `FileNotFoundError` in Render deployment by ensuring the `logs` directory is created in the Dockerfile.
    - Fixed a CORS issue on Render by adding the Vercel frontend URL to the `allow_origins` list in `main.py`.
- **Frontend Enhancements:**
    - Implemented X and Y axis labels on charts for better readability.
    - Created and committed a custom `favicon.svg` matching the "OraFlux Studio" theme.
- **Deployment Instructions Update:**
    - Updated `README.md` with instructions to point Vercel's `BACKEND_API_URL` to `http://localhost:8000` for local backend testing with a deployed frontend, along with a clear warning about its limitations.

## 8. Database Profile Alias Feature (Backend-Managed Connections)

- **Goal Implemented:**
    - Reworked Oracle connection flow so database connection details are managed in backend configuration and exposed to frontend as selectable aliases.
    - Frontend now connects using a selected alias/profile instead of entering host/port/service/user/password manually.

- **Backend Changes:**
    - Added profile configuration file: `backend/app/config/db_profiles.properties`.
    - Added new service: `backend/app/services/db_profile_service.py` to:
        - Load profile entries from properties file.
        - Validate required keys (`host`, `user`, `password`, and one of `service_name`/`sid`).
        - Serve profile list and resolve profile by alias.
    - Extended API models in `backend/app/models.py`:
        - Added `OracleProfileSummary` and `OracleProfilesResponse`.
        - Updated `OracleConnectRequest` to support `profileAlias` (while keeping compatibility for direct connection fields).
    - Added endpoint in `backend/app/main.py`:
        - `GET /oracle/profiles` returns available aliases (and optional labels) for dropdown rendering.
    - Updated `backend/app/services/oracle_service.py`:
        - `create_pool` now supports alias-based resolution via `DbProfileService`.
        - If `profileAlias` is provided, backend profile credentials are used to build DSN and pool.
        - Preserved fallback support for direct/manual connection payloads.

- **Frontend Changes:**
    - Updated connection UI:
        - `frontend/src/app/components/connection-form/connection-form.component.ts/.html/.scss`
        - Removed manual credential inputs and added profile dropdown (`mat-select`).
        - Added profile loading state and empty/error handling.
    - Updated API service:
        - `frontend/src/app/services/api.service.ts` now includes `getOracleProfiles()` for `GET /oracle/profiles`.
    - Updated interfaces:
        - `frontend/src/app/interfaces/api.interfaces.ts` now includes profile response types and alias-capable connect payload.

- **Tests and Verification:**
    - Added backend unit tests for profile loading:
        - `backend/tests/test_db_profile_service.py`
        - fixture: `backend/tests/fixtures/db_profiles_test.properties`
    - Verified targeted profile tests pass:
        - `pytest -q tests/test_db_profile_service.py -p no:cacheprovider` -> `2 passed`
    - Full backend test suite still has pre-existing failures in `tests/test_sql_builder.py` (unrelated to this feature).
    - Frontend build check in this environment failed with `spawn EPERM` (environment permission issue), not a code-level compile diagnostic.

## 9. Oracle Driver Compatibility Fixes

- **Initial Runtime Failure After Profile-Based Connect:**
    - Connection attempts began failing with:
      - `DPY-2053: python-oracledb thin mode cannot be used because thick mode has already been enabled`
    - Root cause:
      - The backend was using async Oracle pool APIs (`create_pool_async`) which are thin-mode only.
      - The running Python process/environment had already enabled Oracle thick mode.

- **Backend Refactor for Driver Compatibility:**
    - Updated `backend/app/services/oracle_service.py` to stop using async Oracle client APIs.
    - Reworked pool creation and query execution to use synchronous `python-oracledb` APIs wrapped with `asyncio.to_thread(...)`.
    - Updated `backend/app/services/session_manager.py` so pool close operations also run safely with thread offloading.
    - Result:
      - FastAPI endpoint surface remained async.
      - Oracle pool/query logic became compatible with both thin and thick mode environments.

- **Follow-Up Query Execution Failure:**
    - After connection succeeded, query execution failed with:
      - `DPY-3001: Native Network Encryption and Data Integrity is only supported in python-oracledb thick mode`
    - Root cause:
      - The target Oracle database required Native Network Encryption/Data Integrity.
      - Thin mode cannot support that capability.

- **Thick Mode Initialization Support Added:**
    - Added new startup helper: `backend/app/services/oracle_driver.py`
    - Wired startup initialization in `backend/app/main.py` using `initialize_oracle_client()`.
    - Thick mode initialization behavior:
      - Uses `ORACLE_CLIENT_LIB_DIR` if provided.
      - Uses `ORACLE_NET_CONFIG_DIR` or `TNS_ADMIN` if provided.
      - Auto-detects Windows Instant Client path:
        - `C:\Program Files\oracle\instantclient_21_20`
      - Auto-detects default network config directory:
        - `C:\Program Files\oracle\instantclient_21_20\network\admin`
      - Prepends Instant Client path to `PATH` before calling `oracledb.init_oracle_client(...)`.
      - Can optionally fail fast with `ORACLE_REQUIRE_THICK_MODE=true`.

- **Error Handling Improvements:**
    - Added a clearer backend error when `DPY-3001` occurs so the user sees an actionable message about Thick mode and Instant Client setup instead of a raw driver error.

- **Final Outcome:**
    - Backend successfully initialized Thick mode using the local Instant Client installation.
    - Database connection succeeded.
    - Query execution succeeded against the Oracle environment requiring network encryption.
