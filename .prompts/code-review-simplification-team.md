# Agent Team: Code Review & Simplification - ZEUES v4.0

## Mission
Review the ZEUES v4.0 codebase to identify opportunities for **simplification and optimization**, focusing on reducing complexity while maintaining functionality. This is a **single-user application** (1 tablet, 1 worker) deployed on Railway + Vercel with Google Sheets as the data source.

## Context
- **Project:** ZEUES v4.0 - Manufacturing pipe spool tracking system
- **Tech Stack:** FastAPI (Python 3.11) + Next.js 14 + TypeScript + Google Sheets
- **Architecture:** Single-user mode (no distributed locks, no real-time sync)
- **Scale:** 30-50 workers, 2,000+ spools, manufacturing floor environment
- **Critical Constraint:** Google Sheets is source of truth (60 writes/min/user, 200-500ms latency)

**Read CLAUDE.md for complete project context before starting.**

## Team Composition

Create an agent team with **4 specialized reviewers** working in parallel:

### 1. Backend Architecture Reviewer (Python/FastAPI)
**Focus:** `backend/` directory (services, repositories, routers, state_machines)

**Simplification targets:**
- Remove unused code, imports, and dependencies
- Identify over-engineered patterns (unnecessary abstractions)
- Detect duplicate logic across services
- Find opportunities to consolidate similar functions
- Review state machine complexity (python-statemachine 2.5.0)
- Check if Clean Architecture layers are justified or over-complicated
- Validate single-user assumptions (are distributed locks still present?)

**Deliverable:** `backend-simplification-report.md` with:
- Files to delete (unused modules)
- Functions to merge (duplicates)
- Patterns to simplify (over-abstraction)
- Code examples (before/after)
- Estimated LOC reduction

### 2. Frontend Simplification Reviewer (Next.js/TypeScript)
**Focus:** `zeues-frontend/` directory (app/, components/, lib/)

**Simplification targets:**
- Remove unused components and utilities
- Identify over-complicated state management (Context API usage)
- Detect redundant API calls or data fetching
- Find opportunities to merge similar pages
- Review TypeScript types (over-specified or `any` abuse)
- Check for CSS/Tailwind duplication
- Validate mobile-first assumptions (unnecessary responsive complexity?)

**Deliverable:** `frontend-simplification-report.md` with:
- Components to remove (unused)
- State to consolidate (Context API)
- API calls to optimize (caching opportunities)
- Type definitions to simplify
- Estimated LOC reduction

### 3. API & Integration Reviewer
**Focus:** API contracts, data flow, Google Sheets integration

**Simplification targets:**
- Identify unused API endpoints (check routers/)
- Detect over-fetching or under-fetching data
- Review Google Sheets column usage (are all 72 columns needed?)
- Find opportunities to batch API calls
- Check for unnecessary validation layers
- Validate error handling complexity (is it over-engineered?)
- Review Metadata event sourcing (is every event necessary?)

**Deliverable:** `api-integration-report.md` with:
- Endpoints to deprecate
- Data models to simplify
- Google Sheets columns to remove (if safe)
- Batching opportunities
- Validation to streamline

### 4. Testing & Documentation Reviewer
**Focus:** `tests/`, `.planning/`, documentation files

**Simplification targets:**
- Identify redundant tests (duplicate coverage)
- Find over-mocked tests (test complexity > code complexity)
- Detect outdated documentation (v2.1, v3.0 references)
- Review `.planning/` files for obsolete content
- Check if all test fixtures are used
- Validate test utility functions (consolidation opportunities)

**Deliverable:** `testing-docs-report.md` with:
- Tests to remove or merge
- Documentation to delete or update
- Test utilities to consolidate
- Planning files to archive

## Team Instructions

### For All Reviewers:
1. **Read CLAUDE.md first** - understand v4.0 architecture and single-user constraints
2. **Use static analysis** - grep, file size checks, import analysis
3. **Provide evidence** - file paths, line numbers, LOC counts
4. **Prioritize impact** - rank findings by complexity reduction vs. effort
5. **Consider risks** - flag high-risk deletions (might break production)
6. **No overlaps** - each reviewer owns their domain exclusively

### Analysis Guidelines:
- **Unused code:** Check imports, function references, dead endpoints
- **Duplication:** Look for copy-paste patterns across files
- **Over-engineering:** Question every abstraction layer (is it justified?)
- **Single-user mode:** Flag any remaining distributed lock code, real-time sync logic
- **Google Sheets limits:** Suggest optimizations for 60 writes/min constraint
- **Mobile-first:** Remove desktop-only complexity (tablets only)

### Output Format (Each Report):
```markdown
# [Domain] Simplification Report

## Executive Summary
- Total files analyzed: X
- Simplification opportunities: Y
- Estimated LOC reduction: Z
- Risk level: Low/Medium/High

## High-Impact Simplifications
1. **[Opportunity Name]**
   - Location: `path/to/file.py:123`
   - Current complexity: [description]
   - Proposed simplification: [description]
   - Impact: -X LOC, -Y functions
   - Risk: Low/Medium/High
   - Effort: 1-5 (days)

## Medium-Impact Simplifications
[Same structure]

## Low-Impact Simplifications
[Same structure]

## Quick Wins (< 1 day effort)
- [ ] Delete `file.py` (unused, 0 references)
- [ ] Merge `functionA()` and `functionB()` (duplicate logic)
- [ ] Remove column `X` from Google Sheets (unused)

## Risks & Warnings
- [Any high-risk deletions that need validation]

## Appendix: Analysis Evidence
[File listings, grep outputs, dependency graphs]
```

## Coordination
- **Lead Agent (Claude):** Collect all 4 reports and synthesize into master plan
- **Debate phase:** Reviewers discuss conflicting recommendations (if any)
- **Final deliverable:** `SIMPLIFICATION-MASTER-PLAN.md` with prioritized action items

## Success Criteria
- ✅ Each reviewer completes their domain analysis independently
- ✅ All reports include LOC reduction estimates
- ✅ Master plan ranks opportunities by ROI (impact/effort)
- ✅ High-risk changes are clearly flagged
- ✅ Quick wins are separated for immediate action

## Model Preference
Use **Sonnet** for each teammate (balance speed + quality for code review).

## Approval Required
**No code changes allowed.** This is a **review and planning exercise only**. All teammates must:
- Read files (static analysis)
- Generate reports (markdown)
- Discuss findings (debate phase)
- **NOT edit any code files**

---

**To launch this team:**
```bash
# Copy this entire file content and paste as a prompt to Claude Code
# Or reference it directly:
"@agent-team Please execute the code review team mission described in .prompts/code-review-simplification-team.md"
```
