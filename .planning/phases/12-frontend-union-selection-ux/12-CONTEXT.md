# Phase 12: Frontend Union Selection UX - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Mobile-first UI that supports dual workflows based on spool version detection:
- **v3.0 spools** → 3-button flow (TOMAR, PAUSAR, COMPLETAR) - unchanged from existing implementation
- **v4.0 spools** → 2-button flow (INICIAR, FINALIZAR) with new union selection page (P5)

This phase delivers the v4.0 user interface for union-level work tracking while maintaining full backward compatibility with v3.0 workflows.

</domain>

<decisions>
## Implementation Decisions

### Union selection interface (P5 - new page)

**Layout:**
- Table with checkbox column (first column), then N_UNION, DN_UNION, TIPO_UNION columns
- Familiar pattern matching existing P4 spool table layout
- 56x56px minimum touch target size for checkboxes (Material Design standard for gloved hands)

**Sticky counter:**
- Position: Sticky header above table (always visible during scroll)
- Content: "Seleccionadas: 7/10 | Pulgadas: 18.5" (1 decimal precision)
- Typography: text-lg (18px) for prominence
- Separator: Bottom border (border-b) to separate from table content
- Loading state: Replace counter with progress bar ("Guardando...") during API call

**Bulk selection:**
- "Seleccionar Todas" button positioned below counter, above table
- Only "Select All" helper (no "Select None") - workers can manually uncheck
- Button applies to available unions only (excludes completed unions)

**Sorting & display:**
- Default sort: N_UNION ascending (natural union order 1, 2, 3...)
- Completed unions: Disabled row with grayed out text + strikethrough + "✓ Armada" or "✓ Soldada" badge
- Completion badges: Green color (success indicator), full text ("✓ Armada" not "✓ ARM")

**Interaction feedback:**
- Checkbox check/uncheck: Instant counter update only (no row highlight or animations)
- Checkbox animation: Subtle fade-in/out (150-200ms) for modern feel
- Long lists (50+ unions): Simple scroll (no pagination or virtualization)

**Table structure:**
- No page title (maximize screen space for table)
- Sticky table header (column headers remain visible during scroll)
- Columns: Checkbox, N_UNION, DN_UNION, TIPO_UNION (minimal, mobile-optimized)

**Continue button:**
- Label: "Continuar" (consistent with existing pages)
- Position: Sticky at bottom of screen (always accessible)
- Size: Matches existing h-20 button standard

### Dual workflow routing

**Version detection on P3:**
- API call on page load: GET /api/uniones/{tag}/metricas
- Logic: total_uniones = 0 → v3.0, total_uniones > 0 → v4.0
- Determines which button set to show (2 vs 3 buttons)

**Button display on P3:**
- v4.0: 2 large buttons (INICIAR, FINALIZAR) - both styled as primary (same color/size)
- v3.0: 3 buttons (TOMAR, PAUSAR, COMPLETAR) - unchanged from existing
- Both button sets use h-20 height for mobile touch targets

**Navigation flows:**
- INICIAR clicked → P3 → P4 (Spool Selection) → API call → P6 (Success)
- FINALIZAR clicked → P3 → P5 (Union Selection) directly (skip P4 - worker knows which spool)
- v3.0 flows unchanged

**Spool filtering on P4:**
- INICIAR action: Show disponibles only (Ocupado_Por IS NULL)
- FINALIZAR action: Show ocupados by current worker (Ocupado_Por = current worker)
- Version badges: Green "v4.0" badge, gray "v3.0" badge (added to P4 table)

**Error routing:**
- Invalid FINALIZAR attempt (worker doesn't own spool): Let backend reject with 403
- No pre-emptive button disabling or empty states

### Confirmation & edge cases

**Zero-selection modal:**
- Trigger: Worker clicks "Continuar" on P5 with 0 unions selected
- Modal text: "¿Liberar sin registrar?"
- Modal buttons: "Liberar Spool" (confirm) + "Cancelar" (go back)
- Confirm action: Call POST /api/v4/occupation/finalizar with empty selected_unions array
- Backend behavior: Logs SPOOL_CANCELADO event, releases lock

**Error handling:**
- 409 Conflict (race condition): Show error modal + reload P5 with fresh data
- 403 Forbidden (ownership): Claude decides error recovery flow
- Network failure: Show error modal with "Reintentar" button (worker controls retry)
- No automatic retries

**Validation strategy:**
- ARM-before-SOLD rule: Backend validation only (no frontend pre-checks)
- Let backend return 403 with clear error message
- Frontend shows error modal, backend is source of truth

**Data loading on P5:**
- Claude decides: Fresh API call vs reuse P4 cache (tradeoff between accuracy and performance)

### Visual consistency

**Color scheme:**
- P5 uses exact same Tailwind colors as existing P1-P6 pages (total consistency)
- No v4.0-specific accent colors or visual differentiation
- Version badges: Green for v4.0, gray for v3.0 (Phase 9 design)

**Button styling:**
- INICIAR and FINALIZAR buttons: Same style (both primary color, equal visual weight)
- No hierarchy or color differentiation between the two actions

**Badge colors:**
- Completion badges ("✓ Armada" / "✓ Soldada"): Green (success color)
- Version badges: Green v4.0, gray v3.0 (informational)

### Claude's Discretion

- Exact error recovery flow for 403 Forbidden (ownership validation failure)
- Data loading strategy for P5: fresh API call vs cached data from P4
- Any spacing, padding, and layout details not explicitly specified
- Responsive breakpoints and mobile-specific optimizations
- Loading spinner styles and animation timing (within "Guardando..." loading bar)

</decisions>

<specifics>
## Specific Ideas

None - no specific product references or "I want it like X" moments. Implementation open to standard mobile-first patterns and React/Next.js best practices.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope. No new capabilities suggested that would belong in other phases.

</deferred>

---

*Phase: 12-frontend-union-selection-ux*
*Context gathered: 2026-02-02*
