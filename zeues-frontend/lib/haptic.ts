/**
 * haptic.ts — Tactile feedback utility for manufacturing floor use.
 *
 * Uses navigator.vibrate (Chrome 32+ on Android, unsupported on iOS).
 * Guards:
 *   - typeof navigator check prevents SSR crashes (Next.js server render)
 *   - 'vibrate' in navigator check skips unsupported browsers silently
 *   - prefers-reduced-motion check respects user accessibility preference
 *
 * Call sites:
 *   hapticTap()     — consequential button presses (worker select)
 *   hapticSuccess() — operation completed successfully (INICIAR/FINALIZAR/MET)
 *   hapticError()   — error state reached (API error, validation failure)
 */

function isHapticAvailable(): boolean {
  if (typeof navigator === 'undefined') return false;
  if (!('vibrate' in navigator)) return false;
  if (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ) {
    return false;
  }
  return true;
}

/** Short tap — for consequential button presses (worker select). */
export function hapticTap(): void {
  if (!isHapticAvailable()) return;
  navigator.vibrate(50);
}

/**
 * Success pattern — double pulse for completed operations.
 * Pattern: vibrate 50ms, pause 50ms, vibrate 100ms.
 */
export function hapticSuccess(): void {
  if (!isHapticAvailable()) return;
  navigator.vibrate([50, 50, 100]);
}

/**
 * Error pattern — triple pulse for errors and failures.
 * Pattern: vibrate 100ms, pause 50ms, vibrate 100ms, pause 50ms, vibrate 100ms.
 */
export function hapticError(): void {
  if (!isHapticAvailable()) return;
  navigator.vibrate([100, 50, 100, 50, 100]);
}
