---
name: Code Review
description: Guidelines for reviewing and improving code quality in YT Lite v3.
---

# Code Review Skill

Use this skill to review code before committing or when refactoring.

## Guidelines

### Python (FastAPI)
- **Type Hinting**: Ensure all functions have type hints.
- **Async**: Use `async def` for I/O bound operations.
- **Error Handling**: Use `try/except` blocks and return appropriate HTTP exceptions.
- **Security**: Validate all inputs. No secrets in source code.

### Frontend
- **CSS**: 
  - Check for hardcoded values (use variables).
  - Check for responsiveness (Flexbox/Grid).
  - Ensure aesthetics match the "Premium Design" goal.
- **JS**: 
  - Ensure no global namespace pollution. Use `const`/`let`.
  - Check for console errors handling.
- **Accessibility**: 
  - Check for `aria-labels` on icon buttons.
  - `alt` tags on images.

### Documentation
- **Docstrings**: Ensure complex logic has docstrings.
- **TODOs**: Mark incomplete items with `TODO`.
