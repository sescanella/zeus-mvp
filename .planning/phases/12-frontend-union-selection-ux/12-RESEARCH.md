# Phase 12: Frontend Union Selection UX - Research

**Researched:** 2026-02-02
**Domain:** React/Next.js mobile-first UI for dual v3.0/v4.0 workflows
**Confidence:** HIGH

## Summary

Phase 12 implements a dual-workflow frontend that dynamically routes users based on spool version detection. The existing v3.0 implementation uses a 3-button flow (TOMAR/PAUSAR/COMPLETAR) with simple spool selection. The new v4.0 flow introduces a 2-button flow (INICIAR/FINALIZAR) with an additional union selection page (P5) for granular work tracking.

The research confirms that the current tech stack (Next.js 14, React 18, Tailwind CSS) is well-suited for this implementation. The existing codebase already has established patterns for checkboxes, tables, and mobile-optimized touch targets. No additional libraries are needed - the implementation can leverage existing components with minor enhancements for sticky headers and real-time counter updates.

**Primary recommendation:** Reuse existing SpoolTable and Checkbox components with modifications for union data, implement sticky positioning with Tailwind utilities, and add a simple modal component using React state (no library needed).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 14.2.0 | React framework with App Router | Already in use, provides SSR/routing |
| React | 18.3.0 | UI library | Existing codebase standard |
| TypeScript | 5.4.0 | Type safety | Project-wide requirement |
| Tailwind CSS | 3.4.0 | Utility-first CSS | Existing styling system |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.562.0 | Icon library | Already used for all icons |
| Native fetch | Built-in | API calls | Existing pattern (no axios) |
| React Context | Built-in | State management | Already used for app state |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom modal | Radix UI Dialog | Radix adds 50KB bundle, custom is simpler for single use |
| React Context | Zustand | Zustand better for complex state, Context sufficient for current needs |
| Manual forms | React Hook Form + Zod | Overkill for checkbox-only form, no text validation needed |

**Installation:**
```bash
# No new packages needed - all requirements met by existing stack
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── seleccionar-union/       # New P5 page for union selection
│   └── page.tsx            # Union selection with checkboxes
├── tipo-interaccion/       # Modified P3 for version detection
│   └── page.tsx            # 2-button vs 3-button display
└── components/
    ├── UnionTable.tsx      # New component (based on SpoolTable)
    ├── Modal.tsx           # New simple modal component
    └── StickyCounter.tsx   # New sticky counter component
```

### Pattern 1: Version Detection on Page Load
**What:** Fetch union metrics on P3 mount to determine spool version
**When to use:** Every time P3 (tipo-interaccion) loads
**Example:**
```typescript
// Source: Next.js 14 best practices
useEffect(() => {
  const detectVersion = async () => {
    const metrics = await fetch(`/api/uniones/${tag}/metricas`);
    const data = await metrics.json();
    const isV4 = data.total_uniones > 0;
    setSpoolVersion(isV4 ? 'v4.0' : 'v3.0');
  };
  detectVersion();
}, [tag]);
```

### Pattern 2: Sticky Header with Scroll
**What:** Fixed position counter that remains visible during table scroll
**When to use:** P5 union selection page
**Example:**
```typescript
// Source: Tailwind CSS documentation
<div className="sticky top-0 z-20 bg-white border-b">
  <div className="p-4 text-lg">
    Seleccionadas: {selected.length}/{total} | Pulgadas: {pulgadas.toFixed(1)}
  </div>
</div>
```

### Pattern 3: Checkbox State Management
**What:** Local state for checkbox selection with real-time updates
**When to use:** Union selection on P5
**Example:**
```typescript
// Source: React 18 patterns
const [selectedUnions, setSelectedUnions] = useState<number[]>([]);

const handleToggle = (unionId: number) => {
  setSelectedUnions(prev =>
    prev.includes(unionId)
      ? prev.filter(id => id !== unionId)
      : [...prev, unionId]
  );
};
```

### Anti-Patterns to Avoid
- **Virtualization for <100 items:** Don't use react-window/virtualized for union lists - unnecessary complexity for typical 10-50 unions per spool
- **Global state for local UI:** Don't lift union selection state to Context - keep it local to P5 page
- **Premature optimization:** Don't implement debouncing for checkbox clicks - React 18 handles batching automatically

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Touch target sizing | Custom touch area calculations | Tailwind min-w/min-h utilities | WCAG compliance built-in, 56px targets with `min-h-14` |
| Scroll position management | Manual scroll tracking | CSS `position: sticky` | Browser-optimized, no JS needed |
| Modal backdrop | Custom overlay with z-index | Portal with `createPortal` | Avoids z-index conflicts |
| Checkbox indeterminate state | Three-state logic | Native indeterminate prop | Browser handles accessibility |

**Key insight:** The existing component library already solves most UI challenges. Focus on composition, not creation.

## Common Pitfalls

### Pitfall 1: Race Conditions in Version Detection
**What goes wrong:** Multiple API calls to detect version cause conflicting UI states
**Why it happens:** User navigates quickly between pages, previous requests complete after new ones
**How to avoid:** Use AbortController to cancel pending requests on unmount
**Warning signs:** UI flickers between 2-button and 3-button layouts

### Pitfall 2: Sticky Header Breaking on iOS Safari
**What goes wrong:** Sticky positioning fails when combined with certain overflow properties
**Why it happens:** iOS Safari has unique viewport handling with address bar
**How to avoid:** Use `overflow-x: clip` instead of `overflow: hidden` on parent containers
**Warning signs:** Header scrolls with content on iOS devices only

### Pitfall 3: Memory Leaks with Real-time Counter
**What goes wrong:** Counter calculations on every render cause performance degradation
**Why it happens:** Calculating pulgadas sum in render function without memoization
**How to avoid:** Use `useMemo` for derived calculations
**Warning signs:** UI becomes sluggish after selecting/deselecting many unions

### Pitfall 4: Touch Target Overlap on Mobile
**What goes wrong:** Checkboxes too close together cause accidental multi-selection
**Why it happens:** Default spacing insufficient for gloved hands in factory
**How to avoid:** Minimum 56px touch targets with 8px spacing
**Warning signs:** Workers report difficulty selecting correct union

## Code Examples

Verified patterns from official sources:

### Modal Component (Simple Implementation)
```typescript
// Source: React 18 documentation
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
}

export function Modal({ isOpen, onClose, onConfirm, title, message }: ModalProps) {
  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white p-6 rounded-lg max-w-sm mx-4">
        <h2 className="text-xl font-bold mb-4">{title}</h2>
        <p className="mb-6">{message}</p>
        <div className="flex gap-4">
          <button
            onClick={onConfirm}
            className="flex-1 h-12 bg-zeues-orange text-white font-bold"
          >
            Liberar Spool
          </button>
          <button
            onClick={onClose}
            className="flex-1 h-12 border-2 border-gray-300"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
```

### Union Selection with Live Counter
```typescript
// Source: React 18 best practices
import { useState, useMemo } from 'react';

function UnionSelectionPage() {
  const [selectedUnions, setSelectedUnions] = useState<number[]>([]);
  const [unions, setUnions] = useState<Union[]>([]);

  // Memoized calculation for performance
  const pulgadasTotal = useMemo(() => {
    return selectedUnions.reduce((sum, unionId) => {
      const union = unions.find(u => u.id === unionId);
      return sum + (union?.dn_union || 0);
    }, 0);
  }, [selectedUnions, unions]);

  return (
    <>
      {/* Sticky Counter */}
      <div className="sticky top-0 z-20 bg-white border-b p-4">
        <div className="text-lg font-semibold">
          Seleccionadas: {selectedUnions.length}/{unions.length} |
          Pulgadas: {pulgadasTotal.toFixed(1)}
        </div>
      </div>

      {/* Union Table */}
      <div className="overflow-y-auto">
        {unions.map(union => (
          <UnionRow
            key={union.id}
            union={union}
            isSelected={selectedUnions.includes(union.id)}
            onToggle={() => handleToggle(union.id)}
            isDisabled={union.completed}
          />
        ))}
      </div>
    </>
  );
}
```

### Touch-Optimized Checkbox Row
```typescript
// Source: Material Design guidelines adapted to Tailwind
function UnionRow({ union, isSelected, onToggle, isDisabled }) {
  return (
    <div
      onClick={() => !isDisabled && onToggle()}
      className={`
        flex items-center gap-4 p-4 min-h-14 cursor-pointer
        ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'active:bg-gray-100'}
      `}
    >
      <input
        type="checkbox"
        checked={isSelected}
        disabled={isDisabled}
        onChange={() => {}} // Handled by row click
        className="w-7 h-7 pointer-events-none" // 28px = 7 * 4px
      />
      <div className="flex-1">
        <span className="text-base">{union.n_union}</span>
        <span className="ml-4 text-gray-600">{union.dn_union}"</span>
      </div>
      {isDisabled && (
        <span className="text-green-600 text-sm">✓ Completada</span>
      )}
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Class components | Function components with hooks | React 16.8 (2019) | Simpler state management |
| Redux for all state | Context + local state | React 18 (2022) | Less boilerplate, better performance |
| CSS modules | Tailwind utilities | Project standard | Faster development, consistent styling |
| Axios for HTTP | Native fetch | Project decision | Smaller bundle, sufficient features |
| React Native for mobile | Responsive web | Industry trend 2023+ | Single codebase, PWA capabilities |

**Deprecated/outdated:**
- PropTypes: Use TypeScript interfaces instead
- componentDidMount: Use useEffect with empty deps
- forceUpdate: Proper state management eliminates need

## Open Questions

Things that couldn't be fully resolved:

1. **Modal animation timing**
   - What we know: Fade-in/out improves UX
   - What's unclear: Optimal duration for factory environment
   - Recommendation: Start with 200ms, adjust based on user feedback

2. **Maximum unions per spool**
   - What we know: Typical range 10-50 unions
   - What's unclear: Maximum possible (100? 200?)
   - Recommendation: Implement simple scroll for now, add virtualization if >100 unions reported

3. **Error recovery for 403**
   - What we know: Backend returns 403 for ownership validation failure
   - What's unclear: Best UX for recovery (redirect vs retry)
   - Recommendation: Show error modal with "Volver" button to P3

## Sources

### Primary (HIGH confidence)
- Next.js 14 documentation - App Router patterns, data fetching
- React 18 documentation - Hooks, state management, portals
- Tailwind CSS documentation - Sticky positioning, responsive utilities
- Existing codebase - SpoolTable, Checkbox components verified working

### Secondary (MEDIUM confidence)
- Material Design touch target guidelines - 48px minimum confirmed
- WCAG 2.2 accessibility standards - 24px minimum with spacing
- React performance articles - Memoization patterns verified

### Tertiary (LOW confidence)
- Community discussions on iOS Safari sticky issues - Workarounds documented but not tested

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing proven stack
- Architecture: HIGH - Patterns match current codebase
- Pitfalls: MEDIUM - Based on known React/CSS issues

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - stable stack)