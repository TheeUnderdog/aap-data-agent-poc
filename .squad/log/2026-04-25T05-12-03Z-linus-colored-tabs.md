# 2026-04-25T05-12-03Z — Linus: Colored Agent Tabs

**Agent:** Linus (Frontend Dev)  
**Status:** Complete  
**Commit:** 165cc4a  

Implemented colored agent tabs with inline SVG injection, per-agent text colors from config, and opacity-based active/inactive styling. All 6 agent icons updated to use `currentColor`, config.js extended with `textColor` per agent, app.js fetches and injects SVGs inline, CSS applies opacity 0.7/0.85/1.0 for inactive/hover/active states.

Files: web/img/*.svg (6), web/config.js, web/js/app.js, web/css/app.css.

Requested by: Dave Grobleski
