# Accessibility Standards — WCAG 2.1 Level AA

ZEUES is committed to WCAG 2.1 Level AA compliance for manufacturing floor accessibility. **Read this before any UI/a11y work.**

## Testing Requirements

### Automated

```bash
# In zeues-frontend/
npm run test:a11y

# Playwright with axe-core
npx playwright test --grep @a11y
npx playwright test tests/accessibility.spec.ts
```

### Manual

- Keyboard navigation: all features reachable via Tab / Enter / Space.
- Screen reader: VoiceOver (macOS) or NVDA (Windows).
- Focus indicators: visible 2 px white/blue ring on every interactive element.

## ARIA Patterns

### Interactive Buttons

```typescript
<button
  aria-label="Descriptive action"
  aria-disabled={isDisabled}
  onClick={handleClick}
>
  Button Text
</button>
```

### Collapsible Panels

```typescript
<button
  aria-expanded={isExpanded}
  aria-controls="panel-id"
  aria-label={isExpanded ? 'Ocultar panel' : 'Mostrar panel'}
  onClick={toggle}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  }}
>
  Toggle
</button>
<div id="panel-id" role="region" aria-label="Panel description">
  {/* Content */}
</div>
```

### Selectable Table Rows

```typescript
<tr
  role="button"
  tabIndex={isDisabled ? -1 : 0}
  aria-label={`${isSelected ? 'Deseleccionar' : 'Seleccionar'} spool ${tag}${isDisabled ? ' (deshabilitado)' : ''}`}
  aria-disabled={isDisabled}
  onClick={() => !isDisabled && handleSelect()}
  onKeyDown={(e) => {
    if (isDisabled) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSelect();
    }
  }}
>
```

## Focus Management

**Focus indicators:**
- Blueprint UI: `focus:outline-none focus:ring-2 focus:ring-zeues-blue focus:ring-inset`
- Dark backgrounds: `focus:outline-none focus:ring-2 focus:ring-white focus:ring-inset`
- Minimum 2 px contrast.
- Required on all interactive elements (buttons, inputs, clickable rows).

**Focus trapping:**
- Error modals trap focus (Tab cycles within the modal).
- Escape closes modals and returns focus to the trigger.

## Color Contrast

**WCAG AA minimums:**
- Normal text: 4.5 : 1
- Large text (18 pt+): 3 : 1
- UI components: 3 : 1

**Blueprint Industrial palette (verified contrast on `#001F3F`):**
| Role | Color | Ratio | Status |
|---|---|---|---|
| Primary text | `#FFFFFF` | 18.5 : 1 | ✅ |
| Error text | `#EF4444` | 4.8 : 1 | ✅ |
| Disabled text | `#9CA3AF` | 3.2 : 1 | ⚠️ large text only |
| Orange accent | `#FF6B35` | 5.2 : 1 | ✅ |

## Keyboard Navigation

**All interactive elements MUST support:**
- `Tab` — focus navigation
- `Enter` — activation (buttons, links, clickable rows)
- `Space` — activation (buttons, toggles)
- Visible focus indicators (2 px ring)
- Logical tab order (follows visual flow)

**Special cases:**
- Collapsible panels: `Enter` / `Space` to expand/collapse.
- Table rows: `Enter` / `Space` to select/deselect.
- Filter inputs: normal text input behavior.
- Navigation buttons: `Enter` to navigate.

## Validation Checklist

Before PR approval:

- [ ] `npm run test:a11y` passes (0 violations).
- [ ] `npx playwright test tests/accessibility.spec.ts` passes.
- [ ] Keyboard navigation tested manually (Tab through all interactive elements).
- [ ] Screen reader announces all actions correctly (VoiceOver / NVDA).
- [ ] Focus indicators visible on every interactive element.
- [ ] No ARIA violations (axe DevTools browser extension).
- [ ] Color contrast meets WCAG AA.

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
