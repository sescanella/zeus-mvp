# MCP Browser Tooling

Claude Code has MCP browser tools for visual testing and production debugging. **Read this before using them.**

## Available Capabilities

```
mcp__MCP_DOCKER__browser_navigate          Navigate to URL
mcp__MCP_DOCKER__browser_snapshot          Capture accessibility tree (preferred)
mcp__MCP_DOCKER__browser_take_screenshot   Visual screenshot
mcp__MCP_DOCKER__browser_click             Click element
mcp__MCP_DOCKER__browser_type              Type into input
mcp__MCP_DOCKER__browser_wait_for          Wait for condition
mcp__MCP_DOCKER__browser_console_messages  Read console errors/warnings
```

## When to Use

**USE for:**
- Visual verification of production deployments (Vercel / Railway).
- UX / UI inspection without running local servers.
- Google Sheets observation (read-only — verify structure).
- API documentation browsing (Swagger UI at `/api/docs`).
- Console error detection in production.
- Cross-environment debugging (staging vs production).
- Screenshot generation for documentation.

**DON'T USE for:**
- Local development testing — use Playwright tests instead.
- Editing Google Sheets — use the gspread API via backend.
- API endpoint testing — use `curl` or Bash.
- Performance testing — use dedicated load-testing tools.

## Production URLs

**Frontend (Vercel):**
```
https://zeues-frontend.vercel.app
```

**Backend API docs (Railway):**
```
https://zeues-backend-mvp-production.up.railway.app/api/docs
```

**Google Sheets (READ-ONLY — never try to edit via browser):**
```
https://docs.google.com/spreadsheets/d/17iOaq2sv4mSOuJY4B8dGQIsWTTUKPspCtb7gk6u-MaQ/edit
```

## Usage Examples

### Verify production deployment

```
browser_navigate  https://zeues-frontend.vercel.app
browser_wait_for  --time 3
browser_snapshot
```

### Check API documentation

```
browser_navigate  https://zeues-backend-mvp-production.up.railway.app/api/docs
browser_wait_for  --time 3
browser_snapshot
```

Expected: Swagger UI with Health, Workers, Spools, Actions sections.

### Inspect Google Sheets structure

```
browser_navigate  https://docs.google.com/spreadsheets/d/.../edit
browser_click     [Uniones tab]
browser_snapshot
```

Expected: 17 columns — `ID`, `OT`, `N_UNION`, `TAG_SPOOL`, `DN_UNION`, etc.

### Debug console errors in production

```
browser_navigate          https://zeues-frontend.vercel.app
browser_console_messages  --level error
```

## Notes

- **Sheets access is read-only** from the browser. To write, use `backend/repositories/sheets_repository.py` + gspread.
- **Playwright config** supports Brave browser — see `zeues-frontend/playwright.config.ts`. `PLAYWRIGHT_BASE_URL` env var targets production.
- **Prefer `browser_snapshot` over `browser_take_screenshot`** — snapshots return structured YAML, easier to analyze programmatically.
