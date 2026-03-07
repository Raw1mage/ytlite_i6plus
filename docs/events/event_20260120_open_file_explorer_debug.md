# Debug Log

## 2026-01-20: Open File Explorer Feature Investigation

### Objective
Enable a button in the web interface to open the local Windows File Explorer at the designated download directory.

### Attempted Solutions
1.  **Frontend File System Access API**:
    *   Tried using `window.showDirectoryPicker` to get a handle.
    *   **Limitation**: Browser security does not reveal the full system path (e.g., `E:\Downloads`), only the directory name. This prevents passing a valid path to the backend.

2.  **Backend Signal File (WATCHER)**:
    *   Implemented a mechanism where the backend writes a signal file (`OPEN_DOWNLOADS.signal`) and a local WSL script (`watcher.sh`) watches for it.
    *   When the signal is detected, `watcher.sh` executes `explorer.exe`.
    *   **Issue**: This works for **Localhost** development where the Browser and Server are on the same machine.

3.  **Cross-Client Limitation (The Blocker)**:
    *   **Scenario**: User is accessing the web app from a Client Device (Laptop), while the Server (Docker) is running on a Host Device.
    *   **Failure**: The `watcher.sh` script runs on the **Server Host**, effectively opening the File Explorer on the Server machine, not the Client machine.
    *   **Conclusion**: Due to browser sandbox security protocols, a web application CANNOT trigger a local system process (like `explorer.exe`) on a remote client machine without installing a specialized native client application.

### Resolution
*   The "Open File Explorer" feature has been removed from the UI as it is technically infeasible for a pure web application in a Client-Server architecture.
*   The system retains the "Silent Save" functionality using the File System Access API, which is the maximum capability allowed by modern browsers.
