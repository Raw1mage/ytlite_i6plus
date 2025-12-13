# Debug Log

## [2025-12-13] Issue: Installing Dependencies on iOS
### Symptom
Installing \`flask\` and \`yt-dlp\` via pip triggered compilation errors for \`MarkupSafe\`.
\`\`\`
ImportError: cannot import name 'CCompilerError' from 'setuptools.errors'
\`\`\`

### Root Cause
The iPhone lacks a C compiler toolchain (clang/gcc) in the default user environment, and the python header files might be missing or mismatched. Some python packages try to build C extensions for performance by default.

### Resolution
- Pip automatically fell back to downloading a pre-compiled wheel (binary) compatible with Darwin/macOS, or a pure Python version.
- **Action:** No manual intervention was eventually needed as \`pip\` handled the fallback, but future packages requiring C extensions (like \`numpy\`) will likely fail and require pre-compiled wheels from iOS-specific repos (like Procursus).

## [2025-12-13] Issue: 'pip' not found
### Symptom
Running \`pip\` command returned command not found, despite Python 3 being installed.
### Root Cause
Python on iOS (via some jailbreak repos) is often a minimal install.
### Resolution
Ran \`python3 -m ensurepip\` to bootstrap pip.
