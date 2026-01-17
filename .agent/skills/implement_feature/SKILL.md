---
name: Implement Feature
description: A workflow for implementing new features in YT Lite v3, covering backend (FastAPI), frontend (templates/static), and design aesthetics.
---

# Implement Feature Skill

This skill guides the implementation of new features for the YT Lite v3 project.

## Context
- **Project Structure**:
  - Middleware (Backend): `webbox/src/middleware/`
    - App Entry: `webbox/src/middleware/main.py`
    - Templates: `webbox/src/middleware/templates/`
    - Static (CSS/JS): `webbox/src/middleware/static/`
- **Tech Stack**:
  - Backend: FastAPI
  - Frontend: HTML5, Vanilla JS, Vanilla CSS (Mobile-first)
  - Templating: Jinja2

## Implementation Workflow

### 1. Planning
- **Analyze Requirements**: Understand the goal (reference `docs/PLAN.md` if applicable).
- **Design UI/UX**:
  - **Mobile First**: Design for small screens (iPhone 6 Plus target).
  - **Aesthetics**: Use vibrant colors, glassmorphism, and smooth animations.
  - **Dynamic**: Use hover effects and micro-animations.
  - **No Placeholders**: Use real data or generated realistic assets.

### 2. Backend Implementation
- **Define Routes**: Add necessary endpoints in `webbox/src/middleware/main.py` or sub-routers.
- **Logic**: Implement integration with Invidious or YouTube Data API.
- **Error Handling**: Ensure 403/404 errors are handled gracefully (fallback strategies).

### 3. Frontend Implementation
- **Templates**: Create or modify HTML templates in `webbox/src/middleware/templates/`.
  - Use semantic HTML5.
  - Ensure unique IDs for interactive elements.
- **Styles**: Add styles to `webbox/src/middleware/static/css/`.
  - Use CSS Variables for consistent theming.
  - Avoid frameworks like Tailwind unless requested; use Vanilla CSS.
- **Interactivity**: Add logic to `webbox/src/middleware/static/js/`.
  - Keep it lightweight (Vanilla JS).
  - Handle loading states and errors visually.

### 4. Verification
- **Test**: Verify the feature works as expected.
- **Review**: Check against the "Design Aesthetics" requirements.
