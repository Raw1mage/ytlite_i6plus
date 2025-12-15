# YT Lite Development SOP

## Application Control
This project uses a helper script `webctl.sh` to manage the Docker containers.

### Restarting the Application
When you modify backend code (Python files in `src/middleware`), you must restart the application for changes to take effect. The frontend (HTML/CSS/JS) typically only requires a page refresh, unless you are modifying build steps (which this project doesn't seem to use heavily for templates).

**Command:**
```bash
./webctl.sh restart
```

### Other Controls
- Start: `./webctl.sh start`
- Stop: `./webctl.sh stop`
- Logs: `./webctl.sh logs`

## Pre-Commit Checklist & SOP
**Objective:** Maintain documentation accuracy and track project history effectively.
**Trigger:** Before executing `git commit`.

**Procedure:**
1.  **Update Progress**:
    - File: `docs/PROGRESS.md`
    - Action: Mark completed tasks, update "Current Status", and refine "Next Steps".
2.  **Update Debug Log**:
    - File: `docs/DEBUGLOG.md`
    - Action: Ensure all recent bugs, fixes, and incidents are recorded.
3.  **Update Documentation (If Applicable)**:
    - File: `README.md`
    - Action: If the project structure, dependencies, or installation steps have changed, update this file.
4.  **Plan Next Steps**:
    - File: `docs/PROGRESS.md` (or `README.md`)
    - Action: Clearly document what will be developed next.

## Troubleshooting & Stability SOP
**Trigger:** If a modification causes the application to break (e.g., black screen, backend errors, layout breakage) or fails to fix the issue.

**Procedure:**
1.  **Stop & Think**: Do not blindly continue.
2.  **Root Cause Analysis**: Investigate why it failed. Check logs, container status, and recent code changes.
3.  **Log**: Record the incident in `docs/DEBUGLOG.md` (project root: `/home/pkcs12/projects/iphone6plus/docs/DEBUGLOG.md`) with:
    - Date/Time
    - What was changed
    - What failed (Symptoms + Error Logs)
    - Root Cause Analysis
4.  **Revert**: Restore the codebase to the last known good state.
5.  **Recovery**: Ensure the environment (Docker, DB) is healthy.
6.  **Retry**: Re-plan and attempt the fix again with the new knowledge.
