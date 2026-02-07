import { ReactNode } from 'react';

interface FooterButton {
  text: string;
  onClick: () => void;
  variant?: 'primary' | 'danger' | 'back';
  icon?: ReactNode;
  disabled?: boolean;
}

interface FixedFooterProps {
  backButton?: FooterButton;
  primaryButton?: FooterButton;
  middleButton?: FooterButton;
}

/**
 * FixedFooter - Reusable dark-themed footer component for ZEUES workflow pages
 *
 * Matches the dark navy theme used across operacion, tipo-interaccion, seleccionar-spool,
 * confirmar, and seleccionar-uniones pages.
 *
 * Supports 2-3 button layouts with consistent dark styling:
 * - Back button (left): White border, white text, active:white bg
 * - Cancel/Middle button (center): Red border for cancel actions
 * - Primary button (right): Orange border for confirm actions
 *
 * Features:
 * - Dark theme (bg-[#001F3F]) with white/red/orange borders
 * - Mobile-first design (800x1280px tablets)
 * - Large touch targets (h-16)
 * - Mono font with tracking for industrial aesthetic
 * - Responsive narrow breakpoint handling
 *
 * @param backButton - Left-aligned back button (optional)
 * @param primaryButton - Right-aligned primary action (optional)
 * @param middleButton - Center-aligned cancel/secondary action (optional)
 *
 * @example
 * // 2-button: Back + Cancel
 * <FixedFooter
 *   backButton={{ text: "VOLVER", onClick: () => router.back(), icon: <ArrowLeft /> }}
 *   primaryButton={{ text: "CANCELAR", onClick: () => router.push('/'), variant: "danger", icon: <X /> }}
 * />
 *
 * @example
 * // 3-button: Back + Pausar + Confirmar
 * <FixedFooter
 *   backButton={{ text: "VOLVER", onClick: handleBack, icon: <ArrowLeft /> }}
 *   middleButton={{ text: "PAUSAR", onClick: handlePause, variant: "danger", icon: <Pause /> }}
 *   primaryButton={{ text: "CONFIRMAR", onClick: handleConfirm, variant: "primary", icon: <Check />, disabled: loading }}
 * />
 */
export function FixedFooter({ backButton, primaryButton, middleButton }: FixedFooterProps) {
  const getButtonStyles = (variant: FooterButton['variant'] = 'primary', disabled: boolean = false) => {
    const baseStyles = `
      flex-1 narrow:w-full h-16
      flex items-center justify-center gap-3
      transition-all duration-200
      group
      ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
    `;

    switch (variant) {
      case 'back':
        return `${baseStyles}
          bg-transparent
          border-4 border-white
          ${!disabled && 'active:bg-white active:text-[#001F3F]'}
        `;
      case 'danger':
        return `${baseStyles}
          bg-transparent
          border-4 border-red-500
          ${!disabled && 'active:bg-red-500 active:border-red-500'}
        `;
      case 'primary':
      default:
        return `${baseStyles}
          bg-transparent
          border-4 border-zeues-orange
          ${!disabled && 'active:bg-zeues-orange active:border-zeues-orange'}
        `;
    }
  };

  const getTextStyles = (variant: FooterButton['variant'] = 'primary', disabled: boolean = false) => {
    const baseStyles = 'text-xl narrow:text-lg font-black font-mono tracking-[0.15em]';

    if (disabled) return `${baseStyles} text-white/50`;

    switch (variant) {
      case 'back':
        return `${baseStyles} text-white group-active:text-[#001F3F]`;
      case 'danger':
        return `${baseStyles} text-red-500 group-active:text-white`;
      case 'primary':
      default:
        return `${baseStyles} text-zeues-orange group-active:text-white`;
    }
  };

  const getIconStyles = (variant: FooterButton['variant'] = 'primary', disabled: boolean = false) => {
    if (disabled) return 'text-white/50';

    switch (variant) {
      case 'back':
        return 'text-white group-active:text-[#001F3F]';
      case 'danger':
        return 'text-red-500 group-active:text-white';
      case 'primary':
      default:
        return 'text-zeues-orange group-active:text-white';
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-[#001F3F] z-50 border-t-4 border-white/30 p-6 tablet:p-5">
      <div className="flex gap-4 tablet:gap-3 narrow:flex-col narrow:gap-3">
        {/* Back button (left) */}
        {backButton && (
          <button
            onClick={backButton.onClick}
            disabled={backButton.disabled}
            className={getButtonStyles('back', backButton.disabled)}
          >
            {backButton.icon && (
              <span className={getIconStyles('back', backButton.disabled)}>
                {backButton.icon}
              </span>
            )}
            <span className={getTextStyles('back', backButton.disabled)}>
              {backButton.text}
            </span>
          </button>
        )}

        {/* Middle button (center) - typically cancel/pause */}
        {middleButton && (
          <button
            onClick={middleButton.onClick}
            disabled={middleButton.disabled}
            className={getButtonStyles(middleButton.variant || 'danger', middleButton.disabled)}
          >
            {middleButton.icon && (
              <span className={getIconStyles(middleButton.variant || 'danger', middleButton.disabled)}>
                {middleButton.icon}
              </span>
            )}
            <span className={getTextStyles(middleButton.variant || 'danger', middleButton.disabled)}>
              {middleButton.text}
            </span>
          </button>
        )}

        {/* Primary button (right) */}
        {primaryButton && (
          <button
            onClick={primaryButton.onClick}
            disabled={primaryButton.disabled}
            className={getButtonStyles(primaryButton.variant || 'primary', primaryButton.disabled)}
          >
            {primaryButton.icon && (
              <span className={getIconStyles(primaryButton.variant || 'primary', primaryButton.disabled)}>
                {primaryButton.icon}
              </span>
            )}
            <span className={getTextStyles(primaryButton.variant || 'primary', primaryButton.disabled)}>
              {primaryButton.text}
            </span>
          </button>
        )}
      </div>
    </div>
  );
}
