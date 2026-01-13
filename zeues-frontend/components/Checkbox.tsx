import { InputHTMLAttributes } from 'react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  id?: string;
}

/**
 * Checkbox component para multiselect de spools (v2.0 batch operations).
 *
 * Features:
 * - Touch-friendly (w-6 h-6 minimum size para tablet)
 * - Accessible (ARIA labels)
 * - Tailwind styling (accent-cyan-600 para tema consistente)
 * - Keyboard navigation (Space/Enter)
 *
 * @example
 * <Checkbox
 *   checked={isSelected}
 *   onChange={(checked) => handleToggle(checked)}
 *   label="MK-1335-CW-25238-011"
 *   id="spool-mk-1335"
 * />
 */
export function Checkbox({
  checked,
  onChange,
  label,
  id,
  disabled,
  className = '',
  ...props
}: CheckboxProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.checked);
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={handleChange}
        disabled={disabled}
        className={`
          w-6 h-6 cursor-pointer
          accent-cyan-600
          rounded
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
        aria-label={label || 'Checkbox'}
        {...props}
      />
      {label && (
        <label
          htmlFor={id}
          className={`
            text-lg text-gray-900 cursor-pointer select-none
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {label}
        </label>
      )}
    </div>
  );
}
